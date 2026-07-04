"""市场上下文数据模型 - Pipeline 各步骤传递的统一数据容器"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from models.ticker import TickerData
from models.kline import KlineData
from models.news import NewsData
from models.fear_greed import FearGreedData
from models.coin_info import CoinInfo
from models.analysis import AnalysisData, TechnicalAnalysis, AIAnalysis
from models.macro import MacroData, MarketStructureData, OnchainPublicData


@dataclass
class MarketContext:
    """
    Pipeline 执行过程中的统一数据容器。
    所有模块只读写这个对象，不直接传递 dict/list。
    """
    # 原始采集数据
    tickers: Dict[str, TickerData] = field(default_factory=dict)
    klines: Dict[str, Dict[str, List[KlineData]]] = field(default_factory=dict)  # {symbol: {timeframe: [kline]}}
    news: Optional[NewsData] = None
    fear_greed: Optional[FearGreedData] = None
    coin_infos: Dict[str, CoinInfo] = field(default_factory=dict)
    macro: Optional[MacroData] = None
    market_structure: Optional[MarketStructureData] = None
    onchain_public: Optional[OnchainPublicData] = None

    # 分析结果
    tech_analyses: Dict[str, Dict[str, TechnicalAnalysis]] = field(default_factory=dict)  # {symbol: {timeframe: TA}}
    analyses: Dict[str, AnalysisData] = field(default_factory=dict)  # {symbol: AnalysisData}

    # 报告
    report_markdown: str = ""
    report_brief: str = ""

    # 元信息
    run_id: str = ""
    run_time: str = ""
    errors: List[str] = field(default_factory=list)
