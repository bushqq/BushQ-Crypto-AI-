"""分析结果数据模型"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from models.base import BaseModel


@dataclass
class TechnicalAnalysis:
    """技术分析结果"""
    symbol: str = ""
    timeframe: str = ""
    ma_signals: Dict[str, str] = field(default_factory=dict)
    rsi: float = 0.0
    rsi_signal: str = ""
    macd_signal: str = ""
    bollinger_position: str = ""
    trend: str = ""  # uptrend / downtrend / sideways
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    summary: str = ""


@dataclass
class AIAnalysis:
    """AI 分析结果"""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_quality: List[Any] = field(default_factory=list)
    macro: Dict[str, Any] = field(default_factory=dict)
    market_structure: Dict[str, Any] = field(default_factory=dict)
    market_summary: str = ""
    risk_alerts: List[Any] = field(default_factory=list)
    market_phase: str = ""  # accumulation / markup / distribution / markdown
    phase_reason: str = ""
    trend_strength: float = 0.0
    market_score: float = 0.0
    bullish_score: float = 0.0
    bearish_score: float = 0.0
    key_observations: List[Any] = field(default_factory=list)
    watch_items: List[Any] = field(default_factory=list)
    news_impact: Any = field(default_factory=dict)
    capital_flow: Dict[str, Any] = field(default_factory=dict)
    onchain_analysis: Dict[str, Any] = field(default_factory=dict)
    sentiment: Dict[str, Any] = field(default_factory=dict)
    position_guidance: Dict[str, Any] = field(default_factory=dict)
    symbol_analysis: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    confidence: str = ""  # high / medium / low
    risk_level: str = ""
    validation: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisData(BaseModel):
    """完整分析结果"""
    symbol: str = ""
    technical: Optional[TechnicalAnalysis] = None
    ai: Optional[AIAnalysis] = None
    fear_greed: Optional[int] = None
