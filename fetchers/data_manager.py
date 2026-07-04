"""DataManager - 统一管理所有 Fetcher，对外提供一站式数据采集接口"""

import logging
from typing import Dict, Optional

from fetchers.okx_fetcher import OKXFetcher
from fetchers.tavily_fetcher import TavilyFetcher
from fetchers.fear_greed_fetcher import FearGreedFetcher
from fetchers.coingecko_fetcher import CoinGeckoFetcher
from fetchers.macro_market_fetcher import MacroMarketFetcher
from models.market_context import MarketContext

logger = logging.getLogger("cic.data_manager")


class DataManager:
    """数据采集管理器 - 统一调度所有 Fetcher"""

    def __init__(self):
        self.okx = OKXFetcher()
        self.tavily = TavilyFetcher()
        self.fear_greed = FearGreedFetcher()
        self.coingecko = CoinGeckoFetcher()
        self.macro_market = MacroMarketFetcher()

    def initialize(self, config) -> None:
        """初始化所有 Fetcher"""
        self.okx.initialize(config)
        self.tavily.initialize(config)
        self.fear_greed.initialize(config)
        self.coingecko.initialize(config)
        self.macro_market.initialize(config)
        logger.info("DataManager 初始化完成")

    def collect_all(self, config) -> MarketContext:
        """
        执行完整数据采集流程，返回 MarketContext。
        任一 Fetcher 失败不阻塞整体流程，只记录错误。
        """
        context = MarketContext()
        symbols = config.get("symbols", [])
        timeframes = config.get("kline.timeframes", ["4h", "1d"])
        kline_limit = config.get("kline.limit", 100)

        # 1. OKX 行情
        try:
            context.tickers = self.okx.fetch_tickers(symbols)
            logger.info("采集行情: %d 个币种", len(context.tickers))
        except Exception as e:
            context.errors.append(f"行情采集失败: {e}")
            logger.error("行情采集失败: %s", e)

        # 2. OKX K线
        try:
            context.klines = self.okx.fetch_klines(symbols, timeframes, kline_limit)
            total = sum(len(klines) for tf_klines in context.klines.values() for klines in tf_klines.values())
            logger.info("采集K线: 共%d根", total)
        except Exception as e:
            context.errors.append(f"K线采集失败: {e}")
            logger.error("K线采集失败: %s", e)

        # 3. Tavily 新闻
        try:
            context.news = self.tavily.fetch_market_news()
            logger.info("采集新闻: %d 条", len(context.news.items) if context.news else 0)
        except Exception as e:
            context.errors.append(f"新闻采集失败: {e}")
            logger.error("新闻采集失败: %s", e)

        # 4. Fear & Greed
        try:
            context.fear_greed = self.fear_greed.fetch()
            if context.fear_greed:
                logger.info("采集情绪指数: %d (%s)", context.fear_greed.value, context.fear_greed.classification)
        except Exception as e:
            context.errors.append(f"情绪指数采集失败: {e}")
            logger.error("情绪指数采集失败: %s", e)

        # 5. CoinGecko 币种信息
        try:
            context.coin_infos = self.coingecko.fetch_all(symbols)
            logger.info("采集币种信息: %d 个", len(context.coin_infos))
        except Exception as e:
            context.errors.append(f"币种信息采集失败: {e}")
            logger.error("币种信息采集失败: %s", e)

        # 6. Funding Rate & Open Interest 补充到 Ticker
        for symbol in symbols:
            try:
                fr = self.okx.fetch_funding_rate(symbol)
                if fr is not None and symbol in context.tickers:
                    context.tickers[symbol].funding_rate = fr
            except Exception:
                pass

            try:
                oi = self.okx.fetch_open_interest(symbol)
                if oi is not None and symbol in context.tickers:
                    context.tickers[symbol].open_interest = oi
            except Exception:
                pass

            try:
                ratio = self.okx.fetch_long_short_ratio(symbol)
                if ratio is not None and symbol in context.tickers:
                    context.tickers[symbol].long_short_ratio = ratio
            except Exception:
                pass

            try:
                oi_trend = self.okx.fetch_open_interest_trend(symbol)
                if symbol in context.tickers:
                    if oi_trend.get("open_interest_usd") is not None:
                        context.tickers[symbol].open_interest_usd = oi_trend["open_interest_usd"]
                    if oi_trend.get("open_interest_change_24h") is not None:
                        context.tickers[symbol].open_interest_change_24h = oi_trend["open_interest_change_24h"]
            except Exception:
                pass

        # 7. 宏观、市场结构、稳定币/DeFi 公开数据
        try:
            macro_bundle = self.macro_market.fetch_all()
            context.macro = macro_bundle.get("macro")
            context.market_structure = macro_bundle.get("market_structure")
            context.onchain_public = macro_bundle.get("onchain_public")
            logger.info(
                "采集宏观/结构数据: DXY=%s BTC.D=%.2f Stablecoin=$%.0f",
                context.macro.dxy.get("value") if context.macro else None,
                context.market_structure.btc_dominance if context.market_structure else 0,
                context.onchain_public.stablecoin_supply_usd if context.onchain_public else 0,
            )
        except Exception as e:
            context.errors.append(f"宏观/市场结构采集失败: {e}")
            logger.error("宏观/市场结构采集失败: %s", e)

        logger.info("数据采集完成，错误: %d 个", len(context.errors))
        return context

    def health_check_all(self) -> Dict[str, bool]:
        """检查所有数据源健康状态"""
        return {
            "okx": self.okx.health_check(),
            "tavily": self.tavily.health_check(),
            "fear_greed": self.fear_greed.health_check(),
            "coingecko": self.coingecko.health_check(),
            "macro_market": self.macro_market.health_check(),
        }

    def close_all(self) -> None:
        """关闭所有 Fetcher"""
        self.okx.close()
        self.tavily.close()
        self.fear_greed.close()
        self.coingecko.close()
        self.macro_market.close()
        logger.info("DataManager 已关闭")
