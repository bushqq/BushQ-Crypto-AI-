"""基础数据模型 - 所有 DTO 的父类"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BaseModel:
    """所有数据模型的基类"""
    id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""
    version: str = "1.0"
