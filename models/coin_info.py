"""币种信息数据模型"""

from dataclasses import dataclass
from typing import Optional
from models.base import BaseModel


@dataclass
class CoinInfo(BaseModel):
    """币种基础信息"""
    symbol: str = ""
    name: str = ""
    chain: str = ""
    sector: str = ""
    market_cap: float = 0.0
    market_cap_rank: int = 0
    circulating_supply: float = 0.0
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    website: str = ""
    description: str = ""
