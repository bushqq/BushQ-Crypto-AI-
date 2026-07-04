"""数据库引擎与会话管理"""

import os
import logging
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("cic.storage")

Base = declarative_base()


class Database:
    """数据库管理器"""

    _instance: Optional["Database"] = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
            cls._instance._session_factory = None
        return cls._instance

    def initialize(self, db_path: str) -> None:
        """初始化数据库连接"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"

        self._engine = create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # SQLite 性能优化
        @event.listens_for(self._engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.close()

        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )

        # 创建所有表
        Base.metadata.create_all(bind=self._engine)
        logger.info("数据库初始化成功: %s", db_path)

    def get_session(self) -> Session:
        """获取数据库会话"""
        if self._session_factory is None:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")
        return self._session_factory()

    def close(self) -> None:
        """关闭数据库连接"""
        if self._engine:
            self._engine.dispose()
            logger.info("数据库连接已关闭")
