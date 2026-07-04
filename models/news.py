"""新闻数据模型"""

from dataclasses import dataclass, field
from typing import List, Optional
from models.base import BaseModel


@dataclass
class NewsItem:
    """单条新闻"""
    title: str = ""
    url: str = ""
    source: str = ""
    published_at: str = ""
    summary: str = ""
    sentiment: str = "neutral"  # positive / negative / neutral
    coins: List[str] = field(default_factory=list)


@dataclass
class NewsData(BaseModel):
    """新闻数据集合"""
    query: str = ""
    items: List[NewsItem] = field(default_factory=list)
    total_count: int = 0
