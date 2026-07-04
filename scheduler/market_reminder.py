"""市场开盘提醒模块"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import schedule

from notifier.wechat_work import WeChatWorkNotifier

logger = logging.getLogger("cic.market_reminder")


class MarketReminder:
    """
    市场开盘提醒。
    在美股/亚股/欧股开盘前1小时推送提醒消息。
    """

    def __init__(self):
        self._notifier: Optional[WeChatWorkNotifier] = None
        self._markets: List[Dict] = []
        self._reminded_today: Dict[str, str] = {}  # {market_name: date_str} 防止重复提醒

    def initialize(self, config: Any, notifier: WeChatWorkNotifier) -> None:
        """初始化提醒器"""
        self._notifier = notifier

        markets = config.get("market_reminder.markets", [])
        self._markets = markets

        if not config.get("market_reminder.enabled", True):
            logger.info("[MarketReminder] 市场提醒已禁用")
            return

        # 注册定时任务
        for market in markets:
            name = market.get("name", "未知市场")
            remind_time = market.get("remind_time", "")
            if remind_time:
                schedule.every().day.at(remind_time).do(self._remind, market=market)
                logger.info("[MarketReminder] 已注册: %s 提醒时间 %s", name, remind_time)

    def _remind(self, market: Dict) -> None:
        """执行提醒"""
        name = market.get("name", "")
        market_info = market.get("market_info", "")
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 防止同一市场同一天重复提醒
        if self._reminded_today.get(name) == today_str:
            return

        self._reminded_today[name] = today_str

        # 构建提醒消息
        message = (
            f"> **{name}提醒**\n\n"
            f"距离 **{market_info}** 还有约1小时\n\n"
            f"当前时间: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"请注意关注市场动态，加密货币市场通常在传统金融市场开盘前后波动加大。"
        )

        if self._notifier:
            success = self._notifier.send(message)
            if success:
                logger.info("[MarketReminder] 已推送: %s", name)
            else:
                logger.error("[MarketReminder] 推送失败: %s", name)
        else:
            logger.info("[MarketReminder] %s: %s", name, market_info)

    def clear_daily_cache(self) -> None:
        """清理每日缓存（每天零点调用）"""
        self._reminded_today.clear()
