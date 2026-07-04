#!/usr/bin/env python3
"""
BushQ Crypto AI - 主入口
AI 驱动的加密货币市场情报分析系统

用法:
    python main.py           # 启动定时调度（每8小时）
    python main.py --once    # 执行一次分析
    python main.py --health  # 检查数据源健康状态
"""

import os
import sys
import argparse

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config_manager import Config
from logger import setup_logger
from fetchers.data_manager import DataManager
from pipeline.pipeline import Pipeline
from scheduler.scheduler import Scheduler


def main():
    parser = argparse.ArgumentParser(description="BushQ Crypto AI")
    parser.add_argument("--once", action="store_true", help="执行一次分析后退出")
    parser.add_argument("--health", action="store_true", help="检查数据源健康状态")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    args = parser.parse_args()

    # 1. 加载配置
    try:
        config = Config.load(args.config)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保 config/config.yaml 存在，或参考 config/config.example.yaml 创建")
        sys.exit(1)

    # 2. 初始化日志
    log_level = config.get("system.log_level", "INFO")
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    setup_logger("cic", log_level, log_dir)

    import logging
    logger = logging.getLogger("cic")
    logger.info("=" * 60)
    logger.info("BushQ Crypto AI v%s", config.get("system.version", "1.0.0"))
    logger.info("=" * 60)

    # 3. 校验配置
    if not config.validate():
        logger.error("配置校验失败，请检查 config/config.yaml")
        sys.exit(1)

    # 4. 健康检查模式
    if args.health:
        logger.info("检查数据源健康状态...")
        dm = DataManager()
        dm.initialize(config)
        results = dm.health_check_all()
        for name, ok in results.items():
            status = "OK" if ok else "UNAVAILABLE"
            logger.info("  %s: %s", name, status)
        dm.close_all()
        return

    # 5. 单次执行模式
    if args.once:
        logger.info("单次执行模式")
        pipeline = Pipeline()
        pipeline.initialize(config)
        context = pipeline.execute()
        if context.errors:
            logger.warning("执行完成但有 %d 个错误", len(context.errors))
        pipeline.close()
        return

    # 6. 常驻调度模式
    scheduler = Scheduler()
    scheduler.initialize(config)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()

    logger.info("系统已退出")


if __name__ == "__main__":
    main()
