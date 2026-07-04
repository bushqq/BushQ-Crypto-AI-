"""恐惧贪婪指数数据模型"""

from dataclasses import dataclass
from typing import Optional
from models.base import BaseModel


@dataclass
class FearGreedData(BaseModel):
    """恐惧贪婪指数"""
    timestamp: str = ""
    value: int = 0
    classification: str = ""  # Extreme Fear / Fear / Neutral / Greed / Extreme Greed
    previous_day: Optional[int] = None
    previous_week: Optional[int] = None
    previous_month: Optional[int] = None
