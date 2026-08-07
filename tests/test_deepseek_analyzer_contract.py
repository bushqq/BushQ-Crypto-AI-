import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.deepseek_analyzer import DeepSeekAnalyzer, _to_ai_analysis


class DeepSeekAnalyzerContractTests(unittest.TestCase):
    def test_incomplete_symbol_response_retries_instead_of_being_accepted(self):
        symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
        partial = _response_for(symbols[:1])
        complete = _response_for(symbols)
        analyzer = DeepSeekAnalyzer()
        analyzer._client = object()
        analyzer._build_user_message = Mock(return_value="{}")
        analyzer._request_completion = Mock(
            side_effect=[json.dumps(partial, ensure_ascii=False), json.dumps(complete, ensure_ascii=False)]
        )
        context = SimpleNamespace(tickers={symbol: object() for symbol in symbols})

        with patch("ai.deepseek_analyzer._apply_context_facts"):
            result = analyzer.analyze(context)

        self.assertIsNotNone(result)
        self.assertEqual(set(symbols), set(result.symbol_analysis))
        self.assertEqual(2, analyzer._request_completion.call_count)

    def test_position_guidance_reason_is_attached_to_explicit_no_trade(self):
        response = _response_for(["SOL-USDT-SWAP"])
        response["position_guidance"] = {
            "by_symbol": [
                {
                    "symbol": "SOL-USDT-SWAP",
                    "reason": "下降趋势延续，但宏观风险高且尚无破位确认。",
                }
            ]
        }

        result = _to_ai_analysis(response)

        self.assertEqual(
            "下降趋势延续，但宏观风险高且尚无破位确认。",
            result.symbol_analysis["SOL-USDT-SWAP"]["trade_reason"],
        )


def _response_for(symbols):
    return {
        "market_phase": {"label": "consolidation", "confidence": "medium", "reason": "震荡"},
        "symbols": [
            {
                "symbol": symbol,
                "state": "震荡",
                "trade_conclusion": "NO_TRADE",
                "technical_summary": "多周期方向不一致。",
                "risk": "尚无有效突破确认。",
                "support": [],
                "resistance": [],
            }
            for symbol in symbols
        ],
        "validation": {"passed": True, "warnings": [], "unsupported_claims_removed": []},
    }


if __name__ == "__main__":
    unittest.main()
