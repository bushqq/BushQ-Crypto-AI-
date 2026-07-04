"""Tavily 新闻采集器"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fetchers.base import BaseFetcher
from models.news import NewsData, NewsItem

logger = logging.getLogger("cic.fetcher.tavily")


class TavilyFetcher(BaseFetcher):
    """Tavily 新闻搜索"""

    def __init__(self):
        super().__init__("Tavily")
        self._api_key: str = ""
        self._max_results: int = 10
        self._total_limit: int = 80
        self._search_depth: str = "advanced"
        self._priority_keywords: List[str] = []
        self._client = None

    def initialize(self, config: Any) -> None:
        """初始化 Tavily 客户端"""
        self._api_key = config.get("news.api_key", "")
        if not self._api_key:
            logger.error("[Tavily] API Key 未配置")
            return

        self._max_results = config.get("news.max_results", 10)
        self._total_limit = config.get("news.total_limit", 80)
        self._search_depth = config.get("news.search_depth", "advanced")
        self._priority_keywords = config.get("news.priority_keywords", [])

        try:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=self._api_key)
            self._initialized = True
            logger.info("[Tavily] 初始化成功")
        except ImportError:
            logger.error("[Tavily] tavily-python 未安装，请运行 pip install tavily-python")
        except Exception as e:
            logger.error("[Tavily] 初始化失败: %s", e)

    def health_check(self) -> bool:
        """检查 Tavily API"""
        if not self._client:
            return False
        try:
            result = self._client.search("crypto", max_results=1)
            return True
        except Exception as e:
            logger.warning("[Tavily] 健康检查失败: %s", e)
            return False

    def fetch(self, query: str = "", **kwargs) -> NewsData:
        """搜索新闻"""
        if not self._client:
            logger.error("[Tavily] 客户端未初始化")
            return NewsData(query=query)

        search_query = query or "cryptocurrency market news today"

        try:
            response = self._client.search(
                query=search_query,
                max_results=self._max_results,
                search_depth=self._search_depth,
                topic="news",
            )

            items = []
            for r in response.get("results", []):
                item = NewsItem(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    source=r.get("source", ""),
                    published_at=r.get("published_date", "") or datetime.utcnow().isoformat(),
                    summary=r.get("content", "")[:500],
                    sentiment="neutral",
                )
                items.append(item)

            news_data = NewsData(
                query=search_query,
                items=items,
                total_count=len(items),
                source="tavily",
            )
            logger.info("[Tavily] 搜索 '%s' 获取 %d 条新闻", search_query, len(items))
            return news_data

        except Exception as e:
            logger.error("[Tavily] 搜索失败: %s", e)
            return NewsData(query=search_query)

    def fetch_coin_news(self, coin: str) -> NewsData:
        """获取特定币种新闻"""
        return self.fetch(query=f"{coin} cryptocurrency news today")

    def fetch_market_news(self) -> NewsData:
        """获取增强版市场综合新闻。"""
        return self.fetch_enhanced_market_news()

    def fetch_enhanced_market_news(self) -> NewsData:
        """
        多查询收集新闻：加密市场、五个币种、宏观事件、金十相关消息。
        无金十 API 时使用 Tavily 搜索金十和宏观关键词。
        """
        queries = [
            "cryptocurrency market analysis Bitcoin Ethereum latest news",
            "crypto market liquidation funding rate ETF regulation latest",
            "Federal Reserve CPI PCE nonfarm payrolls US dollar crypto market",
            "site:jin10.com 美联储 CPI 非农 美股 美元 加密货币 比特币",
            "金十数据 美联储 CPI 非农 美股 美元 比特币 加密货币",
            "BTC Bitcoin ETF SEC whale liquidation latest news",
            "ETH Ethereum ETF regulation latest news",
            "SOL Solana ecosystem latest news",
            "LTC Litecoin market latest news",
            "DOGE Dogecoin market latest news",
        ]

        seen = set()
        items: List[NewsItem] = []
        for query in queries:
            news = self.fetch(query=query)
            for item in news.items:
                key = self._dedupe_key(item)
                if not key or key in seen:
                    continue
                seen.add(key)
                items.append(item)

        items.sort(key=self._importance_score, reverse=True)
        limited = items[: self._total_limit]
        logger.info("[Tavily] 增强新闻收集: %d 条，保留 %d 条", len(items), len(limited))
        return NewsData(
            query="enhanced crypto + macro + jin10",
            items=limited,
            total_count=len(limited),
            source="tavily",
        )

    def _dedupe_key(self, item: NewsItem) -> str:
        """按 URL 域名路径或标题去重。"""
        if item.url:
            parsed = urlparse(item.url)
            return f"{parsed.netloc.lower()}{parsed.path.lower()}".rstrip("/")
        return item.title.strip().lower()

    def _importance_score(self, item: NewsItem) -> int:
        """根据标题、摘要、来源中的重要关键词粗排新闻。"""
        text = f"{item.title} {item.summary} {item.source} {item.url}".lower()
        score = 0
        for keyword in self._priority_keywords:
            if keyword.lower() in text:
                score += 5
        if any(word in text for word in ["breaking", "urgent", "突发", "快讯", "重磅"]):
            score += 8
        if any(word in text for word in ["jin10", "金十", "federal reserve", "美联储"]):
            score += 6
        if any(word in text for word in ["bitcoin", "ethereum", "btc", "eth", "solana", "dogecoin", "litecoin"]):
            score += 2
        return score

    def validate(self, data: Any) -> bool:
        return isinstance(data, NewsData) and len(data.items) > 0

    def normalize(self, raw_data: Any) -> Any:
        return raw_data  # fetch 方法已返回标准模型
