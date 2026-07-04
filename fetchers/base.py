"""Fetcher 基类 - 所有数据采集器必须实现此接口"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("cic.fetcher")


class BaseFetcher(ABC):
    """
    统一 Fetcher 接口。
    所有第三方接口必须经过 Adapter（Fetcher），返回统一 Data Model。
    """

    def __init__(self, name: str):
        self.name = name
        self._initialized = False

    @abstractmethod
    def initialize(self, config: Any) -> None:
        """初始化 Fetcher（加载配置、建立连接等）"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查，返回数据源是否可用"""
        pass

    @abstractmethod
    def fetch(self, **kwargs) -> Any:
        """执行数据采集"""
        pass

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """校验采集到的数据"""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> Any:
        """将原始数据转换为统一 Data Model"""
        pass

    def close(self) -> None:
        """清理资源"""
        self._initialized = False
        logger.info("[%s] 已关闭", self.name)
