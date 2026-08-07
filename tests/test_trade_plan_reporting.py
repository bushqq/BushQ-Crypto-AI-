import tempfile
import unittest

from report.report_generator import ReportGenerator
from risk.trade_plan import TradePlanEngine, TradePlanSettings
from tests.test_trade_plan_engine import _context_for


class TradePlanReportingTests(unittest.TestCase):
    def test_report_contains_executable_trade_plan_prices(self):
        symbol = "SOL-USDT-SWAP"
        context = _context_for(
            symbol=symbol,
            price=72.61,
            state="下降趋势",
            conclusion="SHORT",
            support=[71.93, 70.51],
            resistance=[74.8, 79.64],
        )
        context.trade_plans = TradePlanEngine(TradePlanSettings()).build(context)

        with tempfile.TemporaryDirectory() as output_dir:
            markdown = ReportGenerator(output_dir=output_dir).generate(context)

        self.assertIn("## 交易计划", markdown)
        self.assertIn("SHORT", markdown)
        self.assertIn("入场区间", markdown)
        self.assertIn("止损点位", markdown)
        self.assertIn("追价失效价", markdown)
        self.assertIn("预计强平价", markdown)
        self.assertIn("TP1", markdown)
        self.assertIn("TP2", markdown)
        self.assertIn("TP3", markdown)


if __name__ == "__main__":
    unittest.main()
