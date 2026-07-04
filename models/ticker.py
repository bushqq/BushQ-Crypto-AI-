"""实时行情数据模型"""

from dataclasses import dataclass, field
from typing import Optional
from models.base import BaseModel


@dataclass
class TickerData(BaseModel):
    """实时行情"""
    symbol: str = ""
    timestamp: str = ""
    price: float = 0.0
    change_1h: float = 0.0
    change_4h: float = 0.0
    change_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    volume_24h: float = 0.0
    quote_volume: float = 0.0
    market_cap: float = 0.0
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    open_interest_change_24h: Optional[float] = None
    long_short_ratio: Optional[float] = None
    bid_price: float = 0.0
    ask_price: float = 0.0
    spread: float = 0.0
    exchange: str = "okx"
