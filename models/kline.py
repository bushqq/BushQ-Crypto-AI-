"""K线数据模型"""

from dataclasses import dataclass
from typing import Optional
from models.base import BaseModel


@dataclass
class KlineData(BaseModel):
    """K线数据"""
    symbol: str = ""
    timestamp: str = ""
    timeframe: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    quote_volume: float = 0.0
    trade_count: int = 0
    taker_buy_volume: float = 0.0
    confirm: bool = False
