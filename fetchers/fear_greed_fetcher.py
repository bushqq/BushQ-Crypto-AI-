"""恐惧贪婪指数采集器 - Alternative.me"""

import logging
from datetime import datetime
from typing import Any, Optional

import requests

from fetchers.base import BaseFetcher
from models.fear_greed import FearGreedData

logger = logging.getLogger("cic.fetcher.fear_greed")


class FearGreedFetcher(BaseFetcher):
    """Alternative.me 恐惧贪婪指数"""

    API_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        super().__init__("FearGreed")

    def initialize(self, config: Any) -> None:
        self._initialized = True
        logger.info("[FearGreed] 初始化成功")

    def health_check(self) -> bool:
        try:
            resp = requests.get(self.API_URL, params={"limit": 1}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def fetch(self, **kwargs) -> Optional[FearGreedData]:
        """获取恐惧贪婪指数"""
        try:
            resp = requests.get(self.API_URL, params={"limit": 4}, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if "data" not in data or len(data["data"]) == 0:
                logger.warning("[FearGreed] 返回数据为空")
                return None

            current = data["data"][0]
            result = FearGreedData(
                timestamp=datetime.utcfromtimestamp(int(current["timestamp"])).isoformat(),
                value=int(current["value"]),
                classification=current["value_classification"],
                source="alternative.me",
            )

            # 历史数据
            if len(data["data"]) >= 2:
                result.previous_day = int(data["data"][1]["value"])
            if len(data["data"]) >= 3:
                result.previous_week = int(data["data"][2]["value"])
            if len(data["data"]) >= 4:
                result.previous_month = int(data["data"][3]["value"])

            logger.info("[FearGreed] 当前值: %d (%s)", result.value, result.classification)
            return result

        except Exception as e:
            logger.error("[FearGreed] 获取失败: %s", e)
            return None

    def validate(self, data: Any) -> bool:
        return isinstance(data, FearGreedData) and 0 <= data.value <= 100

    def normalize(self, raw_data: Any) -> Any:
        return raw_data
