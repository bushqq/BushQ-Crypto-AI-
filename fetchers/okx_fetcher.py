"""OKX 交易所数据采集器"""

import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import ccxt

from fetchers.base import BaseFetcher
from models.ticker import TickerData
from models.kline import KlineData

logger = logging.getLogger("cic.fetcher.okx")


class OKXFetcher(BaseFetcher):
    """OKX 交易所数据采集"""

    def __init__(self):
        super().__init__("OKX")
        self._exchange: Optional[ccxt.okx] = None
        self._proxy: str = ""
        self._rate_limit: int = 200

    def initialize(self, config: Any) -> None:
        """初始化 OKX 连接"""
        proxy = config.get("exchange.proxy", "")
        rate_limit = config.get("exchange.options", {}).get("rateLimit", 200)

        exchange_config = {
            "enableRateLimit": True,
            "rateLimit": rate_limit,
            "options": {"defaultType": "swap"},
        }

        if proxy:
            exchange_config["proxies"] = {
                "http": proxy,
                "https": proxy,
            }
            self._proxy = proxy

        self._exchange = ccxt.okx(exchange_config)
        self._exchange.load_markets()
        self._rate_limit = rate_limit
        self._initialized = True
        logger.info("[OKX] 初始化成功 (proxy=%s)", "有" if proxy else "无")

    def health_check(self) -> bool:
        """检查 OKX API 是否可达"""
        if not self._exchange:
            return False
        try:
            self._exchange.fetch_time()
            return True
        except Exception as e:
            logger.warning("[OKX] 健康检查失败: %s", e)
            return False

    def fetch(self, **kwargs) -> Any:
        """通用 fetch 入口，由 DataManager 按方法调用"""
        raise NotImplementedError("请使用 fetch_ticker / fetch_kline 等具体方法")

    def validate(self, data: Any) -> bool:
        """校验数据"""
        if data is None:
            return False
        if isinstance(data, list):
            return len(data) > 0
        if isinstance(data, dict):
            return len(data) > 0
        return True

    def normalize(self, raw_data: Any) -> Any:
        """由具体方法内部处理"""
        raise NotImplementedError("normalize 在各 fetch 方法内部完成")

    # ==================== Ticker ====================

    def fetch_ticker(self, symbol: str) -> TickerData:
        """获取实时行情"""
        try:
            market_symbol = self._to_ccxt_symbol(symbol)
            raw = self._exchange.fetch_ticker(market_symbol)
            pct = float(raw.get("percentage", 0) or 0)
            abs_change = float(raw.get("change", 0) or 0)
            ticker = TickerData(
                symbol=symbol,
                timestamp=datetime.utcnow().isoformat(),
                price=float(raw.get("last", 0)),
                change_1h=0.0,  # ccxt ticker 不提供1h变化，后续从K线计算
                change_24h=pct,  # 百分比涨跌幅
                high_24h=float(raw.get("high", 0) or 0),
                low_24h=float(raw.get("low", 0) or 0),
                volume_24h=float(raw.get("baseVolume", 0) or 0),
                quote_volume=float(raw.get("quoteVolume", 0) or 0),
                bid_price=float(raw.get("bid", 0) or 0),
                ask_price=float(raw.get("ask", 0) or 0),
                spread=float(raw.get("ask", 0)) - float(raw.get("bid", 0)) if raw.get("bid") and raw.get("ask") else 0.0,
                exchange="okx",
                source="okx",
            )
            logger.info("[OKX] Ticker: %s price=%.2f", symbol, ticker.price)
            return ticker
        except Exception as e:
            logger.error("[OKX] 获取 Ticker 失败 %s: %s", symbol, e)
            return TickerData(symbol=symbol, source="okx")

    def fetch_tickers(self, symbols: List[str]) -> Dict[str, TickerData]:
        """批量获取行情"""
        result = {}
        for symbol in symbols:
            result[symbol] = self.fetch_ticker(symbol)
            time.sleep(self._rate_limit / 1000.0)
        return result

    # ==================== K线 ====================

    def fetch_kline(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> List[KlineData]:
        """获取K线数据"""
        try:
            market_symbol = self._to_ccxt_symbol(symbol)
            raw_klines = self._exchange.fetch_ohlcv(market_symbol, timeframe, limit=limit)
            klines = []
            for k in raw_klines:
                kline = KlineData(
                    symbol=symbol,
                    timestamp=datetime.utcfromtimestamp(k[0] / 1000).isoformat(),
                    timeframe=timeframe,
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    source="okx",
                )
                klines.append(kline)
            logger.info("[OKX] K线: %s %s 共%d根", symbol, timeframe, len(klines))
            return klines
        except Exception as e:
            logger.error("[OKX] 获取K线失败 %s %s: %s", symbol, timeframe, e)
            return []

    def fetch_klines(self, symbols: List[str], timeframes: List[str], limit: int = 100) -> Dict[str, Dict[str, List[KlineData]]]:
        """批量获取K线"""
        result = {}
        for symbol in symbols:
            result[symbol] = {}
            for tf in timeframes:
                result[symbol][tf] = self.fetch_kline(symbol, tf, limit)
                time.sleep(self._rate_limit / 1000.0)
        return result

    # ==================== Funding Rate ====================

    def fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """获取资金费率"""
        try:
            market_id = self._to_okx_inst_id(symbol)
            response = self._exchange.public_get_public_funding_rate({
                "instId": market_id,
            })
            if response and "data" in response and len(response["data"]) > 0:
                rate = float(response["data"][0].get("fundingRate", 0))
                logger.info("[OKX] Funding Rate: %s = %.6f", symbol, rate)
                return rate
        except Exception as e:
            logger.warning("[OKX] 获取 Funding Rate 失败 %s: %s", symbol, e)
        return None

    # ==================== Open Interest ====================

    def fetch_open_interest(self, symbol: str) -> Optional[float]:
        """获取持仓量"""
        try:
            market_id = self._to_okx_inst_id(symbol)
            response = self._exchange.public_get_public_open_interest({
                "instId": market_id,
            })
            if response and "data" in response and len(response["data"]) > 0:
                oi = float(response["data"][0].get("oi", 0))
                logger.info("[OKX] Open Interest: %s = %.4f", symbol, oi)
                return oi
        except Exception as e:
            logger.warning("[OKX] 获取 Open Interest 失败 %s: %s", symbol, e)
        return None

    def fetch_long_short_ratio(self, symbol: str) -> Optional[float]:
        """获取最近一条账户多空比。"""
        try:
            market_symbol = self._to_ccxt_symbol(symbol)
            records = self._exchange.fetch_long_short_ratio_history(market_symbol, "5m", limit=1)
            if records:
                ratio = records[-1].get("longShortRatio")
                if ratio is not None:
                    value = float(ratio)
                    logger.info("[OKX] Long/Short Ratio: %s = %.4f", symbol, value)
                    return value
        except Exception as e:
            logger.warning("[OKX] 获取 Long/Short Ratio 失败 %s: %s", symbol, e)
        return None

    def fetch_open_interest_trend(self, symbol: str) -> Dict[str, Optional[float]]:
        """获取 1D OI 历史，计算最近两条的变化率。"""
        result: Dict[str, Optional[float]] = {
            "open_interest_usd": None,
            "open_interest_change_24h": None,
        }
        try:
            base = self._to_okx_inst_id(symbol).split("-", 1)[0]
            records = self._exchange.fetch_open_interest_history(base, "1d", limit=2)
            if not records:
                return result
            latest = records[-1]
            previous = records[-2] if len(records) >= 2 else None
            latest_value = latest.get("openInterestValue") or latest.get("openInterestAmount")
            if latest_value is not None:
                result["open_interest_usd"] = float(latest_value)
            if previous:
                previous_value = previous.get("openInterestValue") or previous.get("openInterestAmount")
                if latest_value is not None and previous_value:
                    prev = float(previous_value)
                    if prev:
                        result["open_interest_change_24h"] = (float(latest_value) - prev) / prev * 100
            logger.info(
                "[OKX] OI Trend: %s usd=%s change24h=%s",
                symbol,
                result["open_interest_usd"],
                result["open_interest_change_24h"],
            )
        except Exception as e:
            logger.warning("[OKX] 获取 OI Trend 失败 %s: %s", symbol, e)
        return result

    @staticmethod
    def _to_okx_inst_id(symbol: str) -> str:
        """转换为 OKX 原生合约 ID，例如 BTC-USDT-SWAP。"""
        if symbol.endswith("-SWAP"):
            return symbol
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
            return f"{base}-{quote}-SWAP"
        return symbol

    @classmethod
    def _to_ccxt_symbol(cls, symbol: str) -> str:
        """转换为 ccxt 永续合约统一符号，例如 BTC/USDT:USDT。"""
        inst_id = cls._to_okx_inst_id(symbol)
        if inst_id.endswith("-USDT-SWAP"):
            base = inst_id.replace("-USDT-SWAP", "")
            return f"{base}/USDT:USDT"
        return symbol

    def close(self) -> None:
        """关闭连接"""
        if self._exchange and hasattr(self._exchange, "close"):
            self._exchange.close()
        super().close()
