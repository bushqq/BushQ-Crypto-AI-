"""Fetcher 模块 - 统一数据采集接口"""

from fetchers.base import BaseFetcher
from fetchers.okx_fetcher import OKXFetcher
from fetchers.tavily_fetcher import TavilyFetcher
from fetchers.fear_greed_fetcher import FearGreedFetcher
from fetchers.coingecko_fetcher import CoinGeckoFetcher
from fetchers.macro_market_fetcher import MacroMarketFetcher
from fetchers.data_manager import DataManager

__all__ = [
    "BaseFetcher",
    "OKXFetcher",
    "TavilyFetcher",
    "FearGreedFetcher",
    "CoinGeckoFetcher",
    "MacroMarketFetcher",
    "DataManager",
]
