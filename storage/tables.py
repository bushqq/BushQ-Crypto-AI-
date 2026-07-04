"""数据库表定义"""

from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, Boolean,
    Index, UniqueConstraint, JSON,
)
from sqlalchemy.sql import func
from storage.database import Base


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text)
    type = Column(String(50))
    description = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CoinInfoTable(Base):
    """币种信息表"""
    __tablename__ = "coin_info"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100))
    chain = Column(String(100))
    sector = Column(String(100))
    market_cap = Column(Float)
    market_rank = Column(Integer, index=True)
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    max_supply = Column(Float)
    website = Column(String(500))
    logo = Column(String(500))
    description = Column(Text)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MarketSnapshot(Base):
    """市场快照表"""
    __tablename__ = "market_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float)
    change_1h = Column(Float)
    change_24h = Column(Float)
    volume = Column(Float)
    funding_rate = Column(Float)
    open_interest = Column(Float)
    fear_greed = Column(Integer)
    btc_dominance = Column(Float)
    market_cap = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_snapshot_symbol_ts", "symbol", "timestamp"),
    )


class KlineTable(Base):
    """K线数据表"""
    __tablename__ = "kline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    quote_volume = Column(Float)
    trade_count = Column(Integer)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_kline"),
        Index("ix_kline_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )


class TechnicalIndicator(Base):
    """技术指标表"""
    __tablename__ = "technical_indicator"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    ma_7 = Column(Float)
    ma_25 = Column(Float)
    ma_99 = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_middle = Column(Float)
    bollinger_lower = Column(Float)
    trend = Column(String(20))
    summary = Column(Text)

    __table_args__ = (
        Index("ix_ti_symbol_tf", "symbol", "timeframe"),
    )


class MarketStructure(Base):
    """市场结构表"""
    __tablename__ = "market_structure"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    trend = Column(String(20))
    support_levels = Column(Text)  # JSON
    resistance_levels = Column(Text)  # JSON
    structure_type = Column(String(50))
    summary = Column(Text)

    __table_args__ = (
        Index("ix_ms_symbol_tf", "symbol", "timeframe"),
    )


class NewsTable(Base):
    """新闻表"""
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000))
    source = Column(String(100))
    published_at = Column(DateTime)
    summary = Column(Text)
    sentiment = Column(String(20))
    coins = Column(Text)  # JSON comma-separated
    query = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_news_published", "published_at"),
    )


class AnalysisHistory(Base):
    """分析历史表"""
    __tablename__ = "analysis_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    technical_summary = Column(Text)
    ai_summary = Column(Text)
    market_phase = Column(String(50))
    risk_alerts = Column(Text)  # JSON
    confidence = Column(String(20))
    fear_greed = Column(Integer)
    raw_data = Column(Text)  # JSON


class ReportTable(Base):
    """报告表"""
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    format = Column(String(20))
    content = Column(Text)
    brief = Column(Text)
    symbols = Column(Text)  # JSON
    file_path = Column(String(500))


class NotificationHistory(Base):
    """推送历史表"""
    __tablename__ = "notification_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    channel = Column(String(50))
    status = Column(String(20))  # success / failed
    message_length = Column(Integer)
    error = Column(Text)
    report_id = Column(Integer)


class SchedulerHistory(Base):
    """调度历史表"""
    __tablename__ = "scheduler_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    action = Column(String(50))  # scheduled / manual / startup
    status = Column(String(20))  # success / failed / timeout
    duration_seconds = Column(Float)
    error = Column(Text)
    run_id = Column(String(100))


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    level = Column(String(20))
    module = Column(String(100))
    message = Column(Text)
    details = Column(Text)


class CacheTable(Base):
    """缓存表"""
    __tablename__ = "cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text)
    expire_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class HealthStatus(Base):
    """健康状态表"""
    __tablename__ = "health_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(100), nullable=False)
    status = Column(String(20))
    last_check = Column(DateTime, server_default=func.now())
    error = Column(Text)
