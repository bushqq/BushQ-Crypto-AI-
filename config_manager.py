"""配置管理模块 - 统一加载 YAML 配置"""

import os
import re
import sys
import yaml
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def _get_project_root():
    """获取项目根目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

_DEFAULT_CONFIG_PATH = os.path.join(_get_project_root(), "config", "config.yaml")
_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")


class Config:
    """统一配置管理器"""

    _instance: Optional["Config"] = None
    _data: Dict[str, Any] = {}
    _loaded_path: Optional[str] = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        """加载配置文件"""
        cls._load_env_file()
        config_path = os.path.abspath(path or _DEFAULT_CONFIG_PATH)
        if cls._loaded_path and cls._loaded_path != config_path:
            raise RuntimeError(
                f"Config is already loaded from {cls._loaded_path}; "
                f"refusing to silently replace it with {config_path}"
            )
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            cls._data = yaml.safe_load(f) or {}
        cls._data = cls._resolve_env_values(cls._data)
        cls._apply_runtime_overrides()
        cls._loaded_path = config_path

        logger.info("配置加载成功: %s", config_path)
        return cls()

    @staticmethod
    def _load_env_file() -> None:
        """加载项目根目录 .env 文件，已存在的系统环境变量优先。"""
        env_path = os.path.join(_get_project_root(), ".env")
        if not os.path.exists(env_path):
            return

        with open(env_path, "r", encoding="utf-8-sig") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value

    @classmethod
    def _resolve_env_values(cls, value: Any) -> Any:
        """递归解析 YAML 中的 ${ENV_VAR} 占位符。"""
        if isinstance(value, dict):
            return {k: cls._resolve_env_values(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._resolve_env_values(item) for item in value]
        if isinstance(value, str):
            match = _ENV_PATTERN.match(value)
            if match:
                return os.environ.get(match.group(1), "")
        return value

    @classmethod
    def _apply_runtime_overrides(cls) -> None:
        """用本地 .env 和 MVP 决策覆盖容易被模板回写的配置。"""
        env_overrides = {
            "news.api_key": "TAVILY_API_KEY",
            "ai.api_key": "DEEPSEEK_API_KEY",
            "ai.model": "DEEPSEEK_MODEL",
            "ai.thinking_mode": "DEEPSEEK_THINKING_MODE",
            "notification.webhook_url": "WECHAT_WORK_WEBHOOK_URL",
        }
        for path, env_key in env_overrides.items():
            value = os.environ.get(env_key)
            if value:
                cls._set(path, value)

        symbols = cls._data.get("symbols", [])
        if isinstance(symbols, list):
            cls._data["symbols"] = [cls._normalize_okx_swap_symbol(s) for s in symbols]

        if os.environ.get("DISABLE_INTERVAL_SCHEDULE", "").lower() in {"1", "true", "yes"}:
            scheduler = cls._data.setdefault("scheduler", {})
            if isinstance(scheduler, dict):
                scheduler.pop("interval_hours", None)

    @classmethod
    def _set(cls, key: str, value: Any) -> None:
        """按点号路径设置配置值。"""
        keys = key.split(".")
        target = cls._data
        for part in keys[:-1]:
            target = target.setdefault(part, {})
        target[keys[-1]] = value

    @staticmethod
    def _normalize_okx_swap_symbol(symbol: str) -> str:
        """MVP 使用 OKX USDT 永续合约标的。"""
        if symbol.endswith("-USDT-SWAP"):
            return symbol
        if symbol.endswith("/USDT"):
            return symbol.replace("/USDT", "-USDT-SWAP")
        return symbol

    @classmethod
    def reload(cls, path: Optional[str] = None) -> "Config":
        """重新加载配置"""
        return cls.load(path)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号路径。
        例: config.get("ai.api_key")
        """
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def validate(self) -> bool:
        """校验必要配置是否存在"""
        required_keys = [
            "system.name",
            "symbols",
            "exchange.provider",
            "ai.provider",
            "database.path",
        ]
        missing = []
        for key in required_keys:
            if self.get(key) is None:
                missing.append(key)

        if missing:
            logger.error("缺少必要配置: %s", ", ".join(missing))
            return False

        # 检查 AI API Key
        if not self.get("ai.api_key"):
            logger.warning("未配置 AI API Key，AI 分析功能将不可用")

        logger.info("配置校验通过")
        return True

    @property
    def raw(self) -> Dict[str, Any]:
        """返回原始配置字典"""
        return self._data.copy()

    def __repr__(self) -> str:
        return f"Config(keys={list(self._data.keys())})"
