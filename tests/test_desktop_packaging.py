import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DesktopPackagingTests(unittest.TestCase):
    def test_package_uses_example_config_and_never_bundles_env(self):
        spec = (ROOT / "BushQCryptoAI.spec").read_text(encoding="utf-8")
        build_script = (ROOT / "打包桌面软件.bat").read_text(encoding="utf-8")
        example_config = (ROOT / "config" / "config.example.yaml").read_text(encoding="utf-8")

        self.assertIn("config/config.example.yaml", spec)
        self.assertNotIn("config/config.yaml", spec)
        self.assertNotIn(".env", spec.lower())
        self.assertNotIn("datas=[('config', 'config')", spec)
        self.assertNotIn('copy ".env"', build_script.lower())
        self.assertNotIn('copy "config\\config.yaml"', build_script.lower())
        self.assertIn('${DEEPSEEK_API_KEY}', example_config)
        self.assertIn('${TAVILY_API_KEY}', example_config)
        self.assertIn('${WECHAT_WORK_WEBHOOK_URL}', example_config)


if __name__ == "__main__":
    unittest.main()
