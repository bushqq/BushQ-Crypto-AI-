"""日志系统模块"""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "cic",
    level: str = "INFO",
    log_dir: Optional[str] = None,
) -> logging.Logger:
    """
    初始化统一日志系统。

    Args:
        name: Logger 名称
        level: 日志级别
        log_dir: 日志文件目录
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 防止重复添加 handler
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（按天轮转，单文件最大 10MB，保留 30 个）
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(
            log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """获取子模块 logger"""
    return logging.getLogger(f"cic.{module_name}")
