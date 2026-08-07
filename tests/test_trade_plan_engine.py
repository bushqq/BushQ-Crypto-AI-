import unittest
from datetime import datetime, timedelta, timezone

from models.analysis import AIAnalysis, AnalysisData, TechnicalAnalysis
from models.kline import KlineData
from models.market_context import MarketContext
from models.ticker import TickerData
from risk.trade_plan import TradePlanEngine, TradePlanSettings


class TradePlanEngineTests(unittest.TestCase):
    def test_downtrend_builds_short_plan_with_ordered_prices(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            conclusion="SHORT",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
        )

        plans = TradePlanEngine(TradePlanSettings()).build(context)

        plan = plans[symbol]
        self.assertEqual("SHORT", plan.conclusion)
        self.assertLess(plan.entry_low, plan.entry_high)
        self.assertGreater(plan.stop_loss, plan.reference_entry)
        self.assertTrue(all(target.price < plan.reference_entry for target in plan.take_profits))
        self.assertEqual([25, 35, 40], [target.close_percent for target in plan.take_profits])
        self.assertLess(plan.chase_invalidation, plan.entry_low)
        self.assertGreater(plan.liquidation_price, plan.stop_loss)

    def test_uptrend_builds_long_plan_with_ordered_prices(self):
        symbol = "LTC-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=45.51,
            state="短期偏强",
            conclusion="LONG",
            support=[43.98, 42.89],
            resistance=[45.81, 48.22],
        )

        plans = TradePlanEngine(TradePlanSettings()).build(context)

        plan = plans[symbol]
        self.assertEqual("LONG", plan.conclusion)
        self.assertLess(plan.entry_low, plan.entry_high)
        self.assertLess(plan.stop_loss, plan.reference_entry)
        self.assertTrue(all(target.price > plan.reference_entry for target in plan.take_profits))
        self.assertGreater(plan.chase_invalidation, plan.entry_high)
        self.assertLess(plan.liquidation_price, plan.stop_loss)

    def test_trade_plan_respects_risk_and_margin_budget(self):
        symbol = "LTC-USDT-SWAP"
        settings = TradePlanSettings(
            risk_capital_usdt=2000,
            risk_per_trade_percent=0.5,
            margin_budget_percent=15,
            max_leverage=3,
            min_reward_risk=1.8,
        )
        context = _context_for(
            symbol=symbol,
            price=45.51,
            state="短期偏强",
            conclusion="LONG",
            support=[43.98, 42.89],
            resistance=[45.81, 48.22],
        )

        plan = TradePlanEngine(settings).build(context)[symbol]

        self.assertEqual(10.0, plan.risk_amount_usdt)
        self.assertGreater(plan.notional_usdt, 0)
        self.assertLessEqual(plan.margin_usdt, 300.0)
        self.assertLessEqual(plan.leverage, 3)
        self.assertGreaterEqual(plan.net_reward_risk, 1.8)
        cost_rate = settings.fee_rate + settings.slippage_rate
        loss = (
            abs(plan.reference_entry - plan.stop_loss)
            + plan.reference_entry * cost_rate
            + plan.stop_loss * cost_rate
        )
        weighted_profit = sum(
            target.close_percent
            / 100
            * (
                abs(target.price - plan.reference_entry)
                - plan.reference_entry * cost_rate
                - target.price * cost_rate
            )
            for target in plan.take_profits
        )
        self.assertAlmostEqual(round(weighted_profit / loss, 2), plan.net_reward_risk, places=2)

    def test_critical_market_risk_blocks_trade_plan(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            conclusion="SHORT",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
            risk_level="critical",
        )

        plan = TradePlanEngine(TradePlanSettings()).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertIsNone(plan.reference_entry)
        self.assertIn("风险", plan.reason)

    def test_state_text_without_structured_conclusion_is_no_trade(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
        )

        plan = TradePlanEngine(TradePlanSettings()).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertIn("结构化", plan.reason)

    def test_explicit_no_trade_uses_the_ai_blocking_reason(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            conclusion="NO_TRADE",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
        )
        context.analyses[symbol].ai.symbol_analysis[symbol]["trade_reason"] = (
            "下降趋势仍在延续，但宏观风险高且尚无有效破位确认。"
        )

        plan = TradePlanEngine(TradePlanSettings()).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertEqual("下降趋势仍在延续，但宏观风险高且尚无有效破位确认。", plan.reason)
        self.assertNotIn("缺少", plan.reason)

    def test_non_okx_swap_symbol_is_blocked(self):
        symbol = "BTC/USDT"
        context = _context_for(
            symbol=symbol,
            price=64000,
            state="上升趋势",
            conclusion="LONG",
            support=[62000],
            resistance=[66000],
        )

        plan = TradePlanEngine(TradePlanSettings()).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertIn("OKX", plan.reason)

    def test_stale_ticker_is_blocked(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            conclusion="SHORT",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
        )
        context.tickers[symbol].timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

        plan = TradePlanEngine(TradePlanSettings(max_data_age_minutes=30)).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertIn("过期", plan.reason)

    def test_invalid_price_geometry_is_no_trade_instead_of_crashing(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=2.0,
            state="上升趋势",
            conclusion="LONG",
            support=[],
            resistance=[3.0],
        )
        for kline in context.klines[symbol]["4h"]:
            kline.high = 4.0
            kline.low = 0.0
            kline.close = 2.0

        plan = TradePlanEngine(TradePlanSettings()).build(context)[symbol]

        self.assertEqual("NO_TRADE", plan.conclusion)
        self.assertIn("风控校验失败", plan.reason)


def _context_for(symbol, price, state, support, resistance, risk_level="medium", conclusion=None):
    now = datetime.now(timezone.utc).isoformat()
    ai = AIAnalysis(
        confidence="medium",
        risk_level=risk_level,
        symbol_analysis={
            symbol: {
                "symbol": symbol,
                "state": state,
                "trade_conclusion": conclusion,
                "support": support,
                "resistance": resistance,
            }
        },
        raw={
            "symbols": [
                {
                    "symbol": symbol,
                    "state": state,
                    "trade_conclusion": conclusion,
                    "support": support,
                    "resistance": resistance,
                }
            ]
        },
    )
    technical = TechnicalAnalysis(
        symbol=symbol,
        timeframe="4h",
        trend=state,
        support_levels=support,
        resistance_levels=resistance,
    )
    klines = []
    for index in range(30):
        close = price + ((index % 5) - 2) * 0.35
        klines.append(
            KlineData(
                symbol=symbol,
                timestamp=now,
                timeframe="4h",
                high=close + 0.8,
                low=close - 0.8,
                close=close,
                confirm=True,
            )
        )
    return MarketContext(
        tickers={symbol: TickerData(symbol=symbol, timestamp=now, price=price)},
        klines={symbol: {"4h": klines}},
        tech_analyses={symbol: {"4h": technical}},
        analyses={symbol: AnalysisData(symbol=symbol, technical=technical, ai=ai)},
    )


if __name__ == "__main__":
    unittest.main()
