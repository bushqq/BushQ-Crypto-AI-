"""CoinGecko 币种信息采集器"""

import time
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from fetchers.base import BaseFetcher
from models.coin_info import CoinInfo

logger = logging.getLogger("cic.fetcher.coingecko")


class CoinGeckoFetcher(BaseFetcher):
    """CoinGecko 币种信息（免费版 API）"""

    BASE_URL = "https://api.coingecko.com/api/v3"

    # 币种映射：交易对 -> CoinGecko ID
    SYMBOL_MAP = {
        "BTC/USDT": "bitcoin",
        "BTC-USDT-SWAP": "bitcoin",
        "ETH/USDT": "ethereum",
        "ETH-USDT-SWAP": "ethereum",
        "SOL/USDT": "solana",
        "SOL-USDT-SWAP": "solana",
        "LTC/USDT": "litecoin",
        "LTC-USDT-SWAP": "litecoin",
        "DOGE/USDT": "dogecoin",
        "DOGE-USDT-SWAP": "dogecoin",
    }

    def __init__(self):
        super().__init__("CoinGecko")
        self._cache: Dict[str, CoinInfo] = {}
        self._cache_hours: int = 6
        self._last_fetch: Dict[str, float] = {}
        self._proxies: Optional[Dict] = None

    def initialize(self, config: Any) -> None:
        self._cache_hours = config.get("coin_info.cache_hours", 6)
        # 使用与交易所相同的代理
        proxy = config.get("exchange.proxy", "")
        if proxy:
            self._proxies = {"http": proxy, "https": proxy}
        self._initialized = True
        logger.info("[CoinGecko] 初始化成功 (缓存%d小时, proxy=%s)", self._cache_hours, "有" if self._proxies else "无")

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.BASE_URL}/ping", timeout=10, proxies=self._proxies)
            return resp.status_code == 200
        except Exception:
            return False

    def fetch(self, symbol: str = "", **kwargs) -> Optional[CoinInfo]:
        """获取币种信息"""
        if not symbol:
            return None

        # 检查缓存
        now = time.time()
        if symbol in self._cache and symbol in self._last_fetch:
            if (now - self._last_fetch[symbol]) < self._cache_hours * 3600:
                logger.debug("[CoinGecko] 使用缓存: %s", symbol)
                return self._cache[symbol]

        coin_id = self.SYMBOL_MAP.get(symbol)
        if not coin_id:
            logger.warning("[CoinGecko] 未知币种: %s", symbol)
            return None

        try:
            resp = requests.get(
                f"{self.BASE_URL}/coins/{coin_id}",
                params={"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"},
                timeout=15,
                proxies=self._proxies,
            )
            resp.raise_for_status()
            data = resp.json()

            coin_info = CoinInfo(
                symbol=symbol,
                name=data.get("name", ""),
                chain="",
                sector=data.get("categories", [""])[0] if data.get("categories") else "",
                market_cap=data.get("market_data", {}).get("market_cap", {}).get("usd", 0) or 0,
                market_cap_rank=data.get("market_cap_rank", 0) or 0,
                circulating_supply=data.get("market_data", {}).get("circulating_supply", 0) or 0,
                total_supply=data.get("market_data", {}).get("total_supply", 0),
                max_supply=data.get("market_data", {}).get("max_supply", 0),
                website=data.get("links", {}).get("homepage", [""])[0] if data.get("links", {}).get("homepage") else "",
                description=(data.get("description", {}).get("en", "") or "")[:500],
                source="coingecko",
            )

            self._cache[symbol] = coin_info
            self._last_fetch[symbol] = now
            logger.info("[CoinGecko] %s: rank=%d mcap=%.0f", symbol, coin_info.market_cap_rank, coin_info.market_cap)
            return coin_info

        except Exception as e:
            logger.error("[CoinGecko] 获取 %s 失败: %s", symbol, e)
            return self._cache.get(symbol)

    def fetch_all(self, symbols: list) -> Dict[str, CoinInfo]:
        """批量获取币种信息"""
        result = {}
        for symbol in symbols:
            info = self.fetch(symbol=symbol)
            if info:
                result[symbol] = info
            time.sleep(1.5)  # 免费版限频
        return result

    def validate(self, data: Any) -> bool:
        return isinstance(data, CoinInfo) and data.name != ""

    def normalize(self, raw_data: Any) -> Any:
        return raw_data
