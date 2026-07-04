"""Scheduler 模块 - 定时任务调度 + 市场开盘提醒"""

import logging
import time
import signal
import sys
from typing import Optional

import schedule

from config_manager import Config
from pipeline.pipeline import Pipeline

logger = logging.getLogger("cic.scheduler")


class Scheduler:
    """
    系统入口 - 控制分析任务的定时执行。
    支持：
    - 市场开盘前1小时执行分析并推送（亚股/欧股/美股）
    - 可选每 N 小时定时执行分析
    - 启动时立即执行
    - 手动触发
    - 优雅退出 (Ctrl+C)
    """

    def __init__(self):
        self._pipeline: Optional[Pipeline] = None
        self._config: Optional[Config] = None
        self._running = False
        self._interval_hours: Optional[int] = None

    def initialize(self, config: Config) -> None:
        """初始化调度器"""
        self._config = config
        self._interval_hours = config.get("scheduler.interval_hours")

        # 初始化 Pipeline
        self._pipeline = Pipeline()
        self._pipeline.initialize(config)

        self._register_market_open_jobs(config)

        if self._interval_hours:
            logger.info("Scheduler 初始化完成 (分析间隔: %d小时)", self._interval_hours)
        else:
            logger.info("Scheduler 初始化完成 (按市场开盘前时间执行)")

    def start(self) -> None:
        """启动调度器"""
        if not self._pipeline:
            logger.error("Scheduler 未初始化")
            return

        self._running = True
        logger.info("Scheduler 已启动")

        # 注册信号处理（Ctrl+C 优雅退出）
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # 启动时立即执行一次
        if self._config.get("scheduler.run_on_start", True):
            logger.info("启动时立即执行一次...")
            self.run_once()

        # 可选：设置定时分析任务（每 N 小时）
        if self._interval_hours:
            schedule.every(self._interval_hours).hours.do(self._run_scheduled, trigger="interval")

        logger.info("定时任务已设置:")
        if self._interval_hours:
            logger.info("  - 间隔分析任务: 每 %d 小时执行一次", self._interval_hours)
        logger.info("  - 开盘前分析任务: 已注册")

        # 打印所有已注册的定时任务
        for job in schedule.get_jobs():
            logger.info("  - %s", job)

        logger.info("按 Ctrl+C 停止...")

        # 主循环
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def run_once(self) -> None:
        """手动执行一次"""
        logger.info("手动执行分析任务...")
        try:
            self._pipeline.execute(send_mode="full")
        except Exception as e:
            logger.error("手动执行失败: %s", e)

    def _run_scheduled(self, trigger: str = "scheduled") -> None:
        """定时执行"""
        logger.info("定时触发分析任务: %s", trigger)
        try:
            self._pipeline.execute(send_mode="full")
        except Exception as e:
            logger.error("定时执行失败: %s", e)

    def _register_market_open_jobs(self, config: Config) -> None:
        """注册主要股市开盘前的完整分析任务。"""
        if not config.get("market_reminder.enabled", True):
            logger.info("开盘前分析任务已禁用")
            return

        markets = config.get("market_reminder.markets", [])
        for market in markets:
            name = market.get("name", "未知市场")
            remind_time = market.get("remind_time")
            if not remind_time:
                continue
            schedule.every().day.at(remind_time).do(self._run_scheduled, trigger=name)
            logger.info("已注册开盘前分析任务: %s %s", name, remind_time)

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        schedule.clear()
        if self._pipeline:
            self._pipeline.close()
        logger.info("Scheduler 已停止")

    def _handle_signal(self, signum, frame) -> None:
        """处理退出信号"""
        logger.info("收到退出信号，正在停止...")
        self.stop()
        sys.exit(0)
