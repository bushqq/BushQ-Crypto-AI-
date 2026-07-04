"""Repository - 数据访问层，禁止业务模块直接执行 SQL"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from storage.database import Database
from storage.tables import (
    CoinInfoTable,
    MarketSnapshot,
    KlineTable,
    TechnicalIndicator,
    MarketStructure,
    NewsTable,
    AnalysisHistory,
    ReportTable,
    NotificationHistory,
    SchedulerHistory,
    SystemLog,
    CacheTable,
)

logger = logging.getLogger("cic.storage")


@contextmanager
def _session_scope():
    """自动管理的数据库会话"""
    session = Database().get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CoinInfoRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            existing = s.query(CoinInfoTable).filter_by(symbol=data["symbol"]).first()
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                s.add(CoinInfoTable(**data))

    @staticmethod
    def get(symbol: str) -> Optional[Dict]:
        with _session_scope() as s:
            row = s.query(CoinInfoTable).filter_by(symbol=symbol).first()
            return {c.name: getattr(row, c.name) for c in row.__table__.columns} if row else None


class MarketSnapshotRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            s.add(MarketSnapshot(**data))

    @staticmethod
    def get_latest(symbol: str) -> Optional[Dict]:
        with _session_scope() as s:
            row = s.query(MarketSnapshot).filter_by(symbol=symbol).order_by(MarketSnapshot.timestamp.desc()).first()
            return {c.name: getattr(row, c.name) for c in row.__table__.columns} if row else None


class KlineRepo:
    @staticmethod
    def save_batch(records: List[Dict]) -> None:
        with _session_scope() as s:
            for r in records:
                existing = s.query(KlineTable).filter_by(
                    symbol=r["symbol"], timeframe=r["timeframe"], timestamp=r["timestamp"]
                ).first()
                if existing:
                    for k, v in r.items():
                        setattr(existing, k, v)
                else:
                    s.add(KlineTable(**r))

    @staticmethod
    def get_recent(symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        with _session_scope() as s:
            rows = s.query(KlineTable).filter_by(symbol=symbol, timeframe=timeframe).order_by(
                KlineTable.timestamp.desc()
            ).limit(limit).all()
            return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in reversed(rows)]


class TechnicalIndicatorRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            s.add(TechnicalIndicator(**data))


class MarketStructureRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        data_copy = data.copy()
        if isinstance(data_copy.get("support_levels"), list):
            data_copy["support_levels"] = json.dumps(data_copy["support_levels"])
        if isinstance(data_copy.get("resistance_levels"), list):
            data_copy["resistance_levels"] = json.dumps(data_copy["resistance_levels"])
        with _session_scope() as s:
            s.add(MarketStructure(**data_copy))


class NewsRepo:
    @staticmethod
    def save_batch(records: List[Dict]) -> None:
        with _session_scope() as s:
            for r in records:
                existing = s.query(NewsTable).filter_by(title=r["title"], source=r.get("source", "")).first()
                if not existing:
                    s.add(NewsTable(**r))

    @staticmethod
    def get_recent(limit: int = 50) -> List[Dict]:
        with _session_scope() as s:
            rows = s.query(NewsTable).order_by(NewsTable.published_at.desc()).limit(limit).all()
            return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]


class AnalysisHistoryRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        data_copy = data.copy()
        if isinstance(data_copy.get("risk_alerts"), list):
            data_copy["risk_alerts"] = json.dumps(data_copy["risk_alerts"])
        if isinstance(data_copy.get("raw_data"), dict):
            data_copy["raw_data"] = json.dumps(data_copy["raw_data"])
        with _session_scope() as s:
            s.add(AnalysisHistory(**data_copy))


class ReportRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> int:
        with _session_scope() as s:
            if isinstance(data.get("symbols"), list):
                data["symbols"] = json.dumps(data["symbols"])
            row = ReportTable(**data)
            s.add(row)
            s.flush()
            return row.id

    @staticmethod
    def get_latest(limit: int = 10) -> List[Dict]:
        with _session_scope() as s:
            rows = s.query(ReportTable).order_by(ReportTable.timestamp.desc()).limit(limit).all()
            return [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]


class NotificationHistoryRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            s.add(NotificationHistory(**data))


class SchedulerHistoryRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            s.add(SchedulerHistory(**data))


class SystemLogRepo:
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        with _session_scope() as s:
            s.add(SystemLog(**data))


class CacheRepo:
    @staticmethod
    def get(key: str) -> Optional[str]:
        with _session_scope() as s:
            now = datetime.utcnow()
            row = s.query(CacheTable).filter(CacheTable.key == key, CacheTable.expire_at > now).first()
            return row.value if row else None

    @staticmethod
    def set(key: str, value: str, expire_hours: int = 1) -> None:
        from datetime import timedelta
        with _session_scope() as s:
            existing = s.query(CacheTable).filter_by(key=key).first()
            expire_at = datetime.utcnow() + timedelta(hours=expire_hours)
            if existing:
                existing.value = value
                existing.expire_at = expire_at
            else:
                s.add(CacheTable(key=key, value=value, expire_at=expire_at))
