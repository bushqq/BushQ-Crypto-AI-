"""Build deterministic research trade plans from an analyzed market snapshot."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from models.market_context import MarketContext


@dataclass(frozen=True)
class TradePlanSettings:
    enabled: bool = True
    risk_capital_usdt: float = 1000.0
    risk_per_trade_percent: float = 1.0
    margin_budget_percent: float = 20.0
    max_leverage: int = 3
    min_reward_risk: float = 1.8
    atr_period: int = 14
    entry_atr_width: float = 0.2
    stop_atr_buffer: float = 0.75
    fee_rate: float = 0.0005
    slippage_rate: float = 0.0005
    max_data_age_minutes: int = 30
    maintenance_margin_rate: float = 0.005
    liquidation_buffer_percent: float = 5.0

    @classmethod
    def from_config(cls, config: Any) -> "TradePlanSettings":
        return cls(
            enabled=bool(config.get("trade_plan.enabled", True)),
            risk_capital_usdt=max(1.0, float(config.get("trade_plan.risk_capital_usdt", 1000))),
            risk_per_trade_percent=max(0.01, float(config.get("trade_plan.risk_per_trade_percent", 1.0))),
            margin_budget_percent=max(0.1, float(config.get("trade_plan.margin_budget_percent", 20.0))),
            max_leverage=max(1, int(config.get("trade_plan.max_leverage", 3))),
            min_reward_risk=max(1.0, float(config.get("trade_plan.min_reward_risk", 1.8))),
            fee_rate=max(0.0, float(config.get("trade_plan.fee_rate", 0.0005))),
            slippage_rate=max(0.0, float(config.get("trade_plan.slippage_rate", 0.0005))),
            max_data_age_minutes=max(1, int(config.get("trade_plan.max_data_age_minutes", 30))),
            maintenance_margin_rate=max(0.0, float(config.get("trade_plan.maintenance_margin_rate", 0.005))),
            liquidation_buffer_percent=max(
                0.0, float(config.get("trade_plan.liquidation_buffer_percent", 5.0))
            ),
        )


@dataclass(frozen=True)
class TradeTarget:
    price: float
    close_percent: int


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    conclusion: str
    reason: str
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    reference_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    chase_invalidation: Optional[float] = None
    liquidation_price: Optional[float] = None
    take_profits: List[TradeTarget] = field(default_factory=list)
    risk_amount_usdt: float = 0.0
    notional_usdt: float = 0.0
    margin_usdt: float = 0.0
    leverage: int = 1
    net_reward_risk: float = 0.0


class TradePlanEngine:
    """Expose one interface for all price, target, and sizing calculations."""

    def __init__(self, settings: TradePlanSettings):
        self.settings = settings

    def build(self, context: MarketContext) -> Dict[str, TradePlan]:
        if not self.settings.enabled:
            return {}
        plans: Dict[str, TradePlan] = {}
        blocked_by_risk = self._market_risk_is_critical(context)
        for symbol, ticker in context.tickers.items():
            if not symbol.endswith("-USDT-SWAP") or str(ticker.exchange).lower() != "okx":
                plans[symbol] = TradePlan(symbol, "NO_TRADE", "第一版仅支持 OKX USDT 永续合约。")
                continue
            if self._is_stale(ticker.timestamp):
                plans[symbol] = TradePlan(symbol, "NO_TRADE", "实时行情已过期，禁止形成交易计划。")
                continue
            if blocked_by_risk:
                plans[symbol] = TradePlan(symbol, "NO_TRADE", "整体风险等级严重，禁止形成交易计划。")
                continue
            detail = self._symbol_detail(context, symbol)
            raw_conclusion = detail.get("trade_conclusion")
            direction = self._direction(raw_conclusion)
            if direction == "NO_TRADE":
                reason = (
                    self._explicit_no_trade_reason(detail)
                    if str(raw_conclusion).strip().upper() == "NO_TRADE"
                    else "缺少 LONG/SHORT 结构化交易结论。"
                )
                plans[symbol] = TradePlan(symbol, "NO_TRADE", reason)
                continue
            try:
                if direction == "LONG":
                    plans[symbol] = self._build_long(context, symbol, ticker.price, detail)
                else:
                    plans[symbol] = self._build_short(context, symbol, ticker.price, detail)
            except (ValueError, ZeroDivisionError, OverflowError) as exc:
                plans[symbol] = TradePlan(symbol, "NO_TRADE", f"风控校验失败：{exc}")
        return plans

    def _is_stale(self, timestamp: str) -> bool:
        if not timestamp:
            return True
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        return age_seconds < -60 or age_seconds > self.settings.max_data_age_minutes * 60

    @staticmethod
    def _market_risk_is_critical(context: MarketContext) -> bool:
        for analysis in context.analyses.values():
            if analysis.ai:
                level = str(analysis.ai.risk_level).strip().lower()
                return level in {"critical", "severe", "严重", "极高"}
        return False

    def _build_long(self, context: MarketContext, symbol: str, price: float, detail: dict) -> TradePlan:
        atr = self._atr(context, symbol, price)
        support = sorted((value for value in self._levels(detail.get("support")) if value < price), reverse=True)
        resistance = sorted(value for value in self._levels(detail.get("resistance")) if value > price)
        anchor = support[0] if support else price - atr * 0.5
        half_width = max(atr * self.settings.entry_atr_width, price * 0.0005)
        entry_low = anchor - half_width
        entry_high = anchor + half_width
        reference = (entry_low + entry_high) / 2
        structural_stop = support[1] if len(support) > 1 else float("inf")
        stop = min(reference - atr * self.settings.stop_atr_buffer, structural_stop)
        self._validate_entry_stop("LONG", entry_low, entry_high, reference, stop)
        chase_invalidation = entry_high + atr * 0.5
        targets, sizing = self._targets_and_sizing(
            direction="LONG",
            reference=reference,
            stop=stop,
            structural_target=resistance[0] if resistance else None,
        )
        return TradePlan(
            symbol=symbol,
            conclusion="LONG",
            reason=str(detail.get("state") or "上升趋势"),
            entry_low=self._round_price(entry_low),
            entry_high=self._round_price(entry_high),
            reference_entry=self._round_price(reference),
            stop_loss=self._round_price(stop),
            chase_invalidation=self._round_price(chase_invalidation),
            take_profits=targets,
            **sizing,
        )

    def _build_short(self, context: MarketContext, symbol: str, price: float, detail: dict) -> TradePlan:
        atr = self._atr(context, symbol, price)
        resistance = sorted(value for value in self._levels(detail.get("resistance")) if value > price)
        support = sorted((value for value in self._levels(detail.get("support")) if value < price), reverse=True)
        anchor = resistance[0] if resistance else price + atr * 0.5
        half_width = max(atr * self.settings.entry_atr_width, price * 0.0005)
        entry_low = anchor - half_width
        entry_high = anchor + half_width
        reference = (entry_low + entry_high) / 2
        structural_stop = resistance[1] if len(resistance) > 1 else 0.0
        stop = max(reference + atr * self.settings.stop_atr_buffer, structural_stop)
        self._validate_entry_stop("SHORT", entry_low, entry_high, reference, stop)
        chase_invalidation = entry_low - atr * 0.5
        if chase_invalidation <= 0:
            raise ValueError("追价失效价必须为正数")
        targets, sizing = self._targets_and_sizing(
            direction="SHORT",
            reference=reference,
            stop=stop,
            structural_target=support[0] if support else None,
        )
        return TradePlan(
            symbol=symbol,
            conclusion="SHORT",
            reason=str(detail.get("state") or "下降趋势"),
            entry_low=self._round_price(entry_low),
            entry_high=self._round_price(entry_high),
            reference_entry=self._round_price(reference),
            stop_loss=self._round_price(stop),
            chase_invalidation=self._round_price(chase_invalidation),
            take_profits=targets,
            **sizing,
        )

    def _targets_and_sizing(
        self,
        direction: str,
        reference: float,
        stop: float,
        structural_target: Optional[float],
    ) -> tuple[List[TradeTarget], dict]:
        unit_risk = abs(reference - stop)
        if not all(math.isfinite(value) for value in (reference, stop, unit_risk)):
            raise ValueError("点位包含非有限数值")
        if reference <= 0 or stop <= 0 or unit_risk <= 0:
            raise ValueError("入场价、止损价或单位风险无效")
        cost_rate = self.settings.fee_rate + self.settings.slippage_rate
        round_trip_cost = reference * cost_rate * 2
        required_factor = max(
            2.0,
            self.settings.min_reward_risk
            + round_trip_cost * (1 + self.settings.min_reward_risk) / unit_risk,
        )
        sign = 1 if direction == "LONG" else -1
        tp1 = reference + sign * unit_risk
        tp2 = reference + sign * unit_risk * required_factor
        tp3 = reference + sign * unit_risk * max(3.0, required_factor + 1.0)
        if structural_target is not None:
            lower, upper = sorted((reference, tp2))
            if lower < structural_target < upper:
                tp1 = structural_target

        loss_per_unit = unit_risk + reference * cost_rate + stop * cost_rate
        target_prices = [tp1, tp2, tp3]
        close_weights = (0.25, 0.35, 0.40)

        def weighted_reward(prices: List[float]) -> float:
            return sum(
                weight * (abs(target - reference) - reference * cost_rate - target * cost_rate)
                for weight, target in zip(close_weights, prices)
            )

        weighted_profit = weighted_reward(target_prices)
        if weighted_profit / loss_per_unit < self.settings.min_reward_risk:
            shortfall = self.settings.min_reward_risk * loss_per_unit - weighted_profit
            target_prices[2] += sign * (shortfall / close_weights[2]) * 1.01

        if not all(math.isfinite(value) and value > 0 for value in target_prices):
            raise ValueError("止盈点位必须为正数")
        tp1, tp2, tp3 = target_prices
        if direction == "LONG" and not reference < tp1 < tp2 < tp3:
            raise ValueError("LONG 止盈点位顺序无效")
        if direction == "SHORT" and not reference > tp1 > tp2 > tp3:
            raise ValueError("SHORT 止盈点位顺序无效")

        risk_budget = self.settings.risk_capital_usdt * self.settings.risk_per_trade_percent / 100
        quantity = risk_budget / loss_per_unit
        margin_budget = self.settings.risk_capital_usdt * self.settings.margin_budget_percent / 100
        max_notional = margin_budget * max(1, self.settings.max_leverage)
        notional = min(quantity * reference, max_notional)
        leverage = min(
            max(1, self.settings.max_leverage),
            max(1, math.ceil(notional / margin_budget)) if margin_budget > 0 else 1,
        )
        buffer_amount = reference * self.settings.liquidation_buffer_percent / 100

        def liquidation_price(value: int) -> float:
            if direction == "LONG":
                return reference * (1 - 1 / value + self.settings.maintenance_margin_rate)
            return reference * (1 + 1 / value - self.settings.maintenance_margin_rate)

        def liquidation_is_safe(value: int) -> bool:
            liquidation = liquidation_price(value)
            if direction == "LONG":
                return liquidation + buffer_amount < stop
            return liquidation - buffer_amount > stop

        while leverage > 1 and not liquidation_is_safe(leverage):
            leverage -= 1
        notional = min(notional, margin_budget * leverage)
        actual_risk = notional / reference * loss_per_unit
        margin = notional / leverage
        liquidation = liquidation_price(leverage)
        if not liquidation_is_safe(leverage):
            raise ValueError("止损与预计强平价之间没有足够安全缓冲")
        rounded_reference = self._round_price(reference)
        rounded_stop = self._round_price(stop)
        rounded_targets = [self._round_price(value) for value in target_prices]
        rounded_loss = (
            abs(rounded_reference - rounded_stop)
            + rounded_reference * cost_rate
            + rounded_stop * cost_rate
        )
        rounded_profit = sum(
            weight
            * (
                abs(target - rounded_reference)
                - rounded_reference * cost_rate
                - target * cost_rate
            )
            for weight, target in zip(close_weights, rounded_targets)
        )
        net_reward_risk = rounded_profit / rounded_loss
        return (
            [
                TradeTarget(rounded_targets[0], 25),
                TradeTarget(rounded_targets[1], 35),
                TradeTarget(rounded_targets[2], 40),
            ],
            {
                "risk_amount_usdt": round(actual_risk, 2),
                "notional_usdt": round(notional, 2),
                "margin_usdt": round(margin, 2),
                "leverage": leverage,
                "liquidation_price": self._round_price(liquidation),
                "net_reward_risk": round(net_reward_risk, 2),
            },
        )

    @staticmethod
    def _symbol_detail(context: MarketContext, symbol: str) -> dict:
        analysis = context.analyses.get(symbol)
        if analysis and analysis.ai:
            detail = analysis.ai.symbol_analysis.get(symbol)
            if isinstance(detail, dict):
                return detail
        return {}

    @staticmethod
    def _direction(state: object) -> str:
        text = str(state).strip().lower()
        if text == "short":
            return "SHORT"
        if text == "long":
            return "LONG"
        return "NO_TRADE"

    @staticmethod
    def _explicit_no_trade_reason(detail: dict) -> str:
        for key in ("trade_reason", "reason", "technical_summary", "risk"):
            value = str(detail.get(key) or "").strip()
            if value:
                return value
        return "AI 综合裁决为 NO_TRADE，当前条件不足以形成交易计划。"

    @staticmethod
    def _levels(values: object) -> Iterable[float]:
        if not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number) and number > 0:
                yield number

    @staticmethod
    def _validate_entry_stop(
        direction: str,
        entry_low: float,
        entry_high: float,
        reference: float,
        stop: float,
    ) -> None:
        values = (entry_low, entry_high, reference, stop)
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("入场区间或止损点位无效")
        if not entry_low < reference < entry_high:
            raise ValueError("参考入场价不在入场区间内")
        if direction == "LONG" and not stop < entry_low:
            raise ValueError("LONG 止损必须低于入场区间")
        if direction == "SHORT" and not stop > entry_high:
            raise ValueError("SHORT 止损必须高于入场区间")

    def _atr(self, context: MarketContext, symbol: str, price: float) -> float:
        frames = context.klines.get(symbol, {})
        klines = frames.get("4h") or frames.get("1d") or []
        recent = klines[-self.settings.atr_period :]
        ranges = [float(item.high) - float(item.low) for item in recent if item.high > item.low]
        return sum(ranges) / len(ranges) if ranges else max(price * 0.02, 0.000001)

    @staticmethod
    def _round_price(value: float) -> float:
        if value >= 1000:
            digits = 1
        elif value >= 1:
            digits = 2
        elif value >= 0.1:
            digits = 4
        else:
            digits = 6
        return round(value, digits)
