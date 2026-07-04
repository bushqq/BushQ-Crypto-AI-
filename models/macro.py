"""宏观、市场结构和公开链上数据模型"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from models.base import BaseModel


@dataclass
class MacroData(BaseModel):
    """宏观市场数据"""
    dxy: Dict[str, Any] = field(default_factory=dict)
    treasury_yields: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class MarketStructureData(BaseModel):
    """加密市场结构数据"""
    total_market_cap_usd: float = 0.0
    total_volume_24h_usd: float = 0.0
    btc_dominance: float = 0.0
    eth_dominance: float = 0.0
    stablecoin_dominance: float = 0.0
    altcoin_dominance: float = 0.0
    dominance_breakdown: Dict[str, float] = field(default_factory=dict)
    sector_rotation: List[Dict[str, Any]] = field(default_factory=list)
    active_cryptocurrencies: int = 0
    markets: int = 0
    summary: str = ""
    errors: List[str] = field(default_factory=list)


@dataclass
class OnchainPublicData(BaseModel):
    """
    免费公开链上/DeFi 代理数据。
    MVP 不接付费 Glassnode/CryptoQuant，因此这里先保存稳定币供应和 DeFi TVL。
    """
    stablecoin_supply_usd: float = 0.0
    stablecoin_assets: List[Dict[str, Any]] = field(default_factory=list)
    defi_tvl_usd: float = 0.0
    status: str = "public_proxy"
    summary: str = ""
    errors: List[str] = field(default_factory=list)
