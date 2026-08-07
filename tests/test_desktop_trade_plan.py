import os
import logging
import tempfile
import unittest
from itertools import combinations
from pathlib import Path
from unittest.mock import patch

import yaml

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QGroupBox, QLineEdit, QScrollArea, QSpinBox

import gui_app


class DesktopTradePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._reset_logger()
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.project_root = Path(self.temp_dir.name)
        (self.project_root / "config").mkdir()
        (self.project_root / "templates" / "prompts").mkdir(parents=True)
        (self.project_root / "data" / "reports").mkdir(parents=True)
        (self.project_root / "logs").mkdir()
        self.config_path = self.project_root / "config" / "config.yaml"
        self.prompt_path = self.project_root / "templates" / "prompts" / "daily_analysis.md"
        self.config_path.write_text(
            yaml.safe_dump(
                {
                    "symbols": ["BTC-USDT-SWAP", "ETH-USDT-SWAP"],
                    "exchange": {"proxy": "http://127.0.0.1:7890"},
                    "ai": {"model": "deepseek-chat", "thinking_mode": "disabled", "prompt_template": "templates/prompts/daily_analysis.md"},
                    "news": {"total_limit": 60},
                    "scheduler": {"auto_push_enabled": True},
                    "trade_plan": {
                        "enabled": True,
                        "risk_capital_usdt": 1500,
                        "risk_per_trade_percent": 1.25,
                        "margin_budget_percent": 20,
                        "max_leverage": 4,
                        "min_reward_risk": 1.8,
                    },
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        self.prompt_path.write_text("Test prompt", encoding="utf-8")
        (self.project_root / ".env").write_text(
            "DEEPSEEK_API_KEY=deepseek-secret\n"
            "TAVILY_API_KEY=tavily-secret\n"
            "WECHAT_WORK_WEBHOOK_URL=https://example.test/webhook\n"
            "DEEPSEEK_MODEL=deepseek-chat\n",
            encoding="utf-8",
        )
        self.root_patch = patch.object(gui_app, "PROJECT_ROOT", self.project_root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self._reset_logger()
        self.temp_dir.cleanup()

    @staticmethod
    def _reset_logger():
        logger = logging.getLogger("cic")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def make_window(self):
        window = gui_app.MainWindow()
        window.tabs.setCurrentWidget(window.settings_tab)
        window.show()
        self.app.processEvents()
        return window

    def test_settings_has_three_groups_scroll_area_and_risk_controls(self):
        window = self.make_window()
        try:
            scroll_area = window.findChild(QScrollArea, "settingsScrollArea")
            self.assertIsNotNone(scroll_area)
            groups = {
                group.objectName(): group.title()
                for group in window.findChildren(QGroupBox)
                if group.objectName().endswith("SettingsGroup")
            }
            self.assertEqual(
                {
                    "interfaceSettingsGroup": "接口配置",
                    "analysisSettingsGroup": "分析设置",
                    "riskSettingsGroup": "交易风控",
                },
                groups,
            )
            self.assertEqual(11, window.trade_plan_table.columnCount())
            self.assertIsInstance(window.risk_capital, QDoubleSpinBox)
            self.assertIsInstance(window.risk_per_trade, QDoubleSpinBox)
            self.assertIsInstance(window.margin_budget, QDoubleSpinBox)
            self.assertIsInstance(window.max_leverage, QSpinBox)
            self.assertIsInstance(window.min_reward_risk, QDoubleSpinBox)
            self.assertEqual(QLineEdit.Password, window.deepseek_key.echoMode())
            self.assertEqual(QLineEdit.Password, window.tavily_key.echoMode())
            self.assertEqual(QLineEdit.Password, window.wechat_webhook.echoMode())
            window.secret_toggle_button.click()
            self.assertEqual(QLineEdit.Normal, window.deepseek_key.echoMode())
            self.assertEqual("隐藏密钥", window.secret_toggle_button.text())
            window.secret_toggle_button.click()
            self.assertEqual(QLineEdit.Password, window.deepseek_key.echoMode())
            self.assertEqual("显示密钥", window.secret_toggle_button.text())
        finally:
            window.close()

    def test_settings_reflow_without_group_overlap(self):
        window = self.make_window()
        try:
            for width, expected_mode in ((1180, "double"), (760, "single")):
                window.resize(width, 680)
                self.app.processEvents()
                self.assertEqual(expected_mode, window.settings_layout_mode)
                groups = [window.interface_settings_group, window.analysis_settings_group, window.risk_settings_group]
                for left, right in combinations(groups, 2):
                    self.assertFalse(left.geometry().intersects(right.geometry()))
                for field in (window.deepseek_key, window.deepseek_model, window.proxy, window.news_total, window.risk_capital):
                    self.assertGreaterEqual(field.height(), 40)
        finally:
            window.close()

    def test_settings_load_and_save_round_trip(self):
        window = self.make_window()
        try:
            self.assertEqual("deepseek-secret", window.deepseek_key.text())
            self.assertEqual("BTC-USDT-SWAP\nETH-USDT-SWAP", window.symbols.toPlainText())
            self.assertEqual(1500, window.risk_capital.value())

            window.deepseek_key.setText("updated-secret")
            window.symbols.setPlainText("SOL-USDT-SWAP\nDOGE-USDT-SWAP, XRP-USDT-SWAP")
            window.news_total.setValue(90)
            window.risk_capital.setValue(2500)
            window.max_leverage.setValue(6)
            window.prompt_edit.setPlainText("Updated prompt")
            with patch.object(gui_app.QMessageBox, "information"):
                window.save_settings()

            saved_env = (self.project_root / ".env").read_text(encoding="utf-8")
            saved_config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            self.assertIn("DEEPSEEK_API_KEY=updated-secret", saved_env)
            self.assertEqual(["SOL-USDT-SWAP", "DOGE-USDT-SWAP", "XRP-USDT-SWAP"], saved_config["symbols"])
            self.assertEqual(90, saved_config["news"]["total_limit"])
            self.assertEqual(2500, saved_config["trade_plan"]["risk_capital_usdt"])
            self.assertEqual(6, saved_config["trade_plan"]["max_leverage"])
            self.assertTrue(saved_config["scheduler"]["auto_push_enabled"])
            self.assertEqual("Updated prompt", self.prompt_path.read_text(encoding="utf-8"))
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
