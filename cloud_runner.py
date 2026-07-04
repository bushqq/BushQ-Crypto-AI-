#!/usr/bin/env python3
"""Headless runner for GitHub Actions and background execution."""

import argparse
import logging
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config_manager import Config
from fetchers.data_manager import DataManager
from logger import setup_logger
from pipeline.pipeline import Pipeline


def _ensure_config(config_path: str) -> None:
    if os.path.exists(config_path):
        return
    example_path = os.path.join(PROJECT_ROOT, "config", "config.example.yaml")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    shutil.copyfile(example_path, config_path)


def run_once(config: Config, send_mode: str) -> int:
    pipeline = Pipeline()
    pipeline.initialize(config)
    try:
        context = pipeline.execute(send_notification=True, send_mode=send_mode)
        if context.errors:
            logging.getLogger("cic").warning("Run finished with %d errors", len(context.errors))
            return 2
        return 0
    finally:
        pipeline.close()


def health_check(config: Config) -> int:
    logger = logging.getLogger("cic")
    dm = DataManager()
    dm.initialize(config)
    try:
        results = dm.health_check_all()
        for name, ok in results.items():
            logger.info("%s: %s", name, "OK" if ok else "UNAVAILABLE")
        return 0 if all(results.values()) else 2
    finally:
        dm.close_all()


def main() -> int:
    parser = argparse.ArgumentParser(description="BushQ Crypto AI headless runner")
    parser.add_argument("--config", default=os.path.join(PROJECT_ROOT, "config", "config.yaml"))
    parser.add_argument("--send-mode", choices=["config", "summary", "full"], default="full")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--create-config", action="store_true", help="Create config.yaml from config.example.yaml if missing")
    args = parser.parse_args()

    if args.create_config:
        _ensure_config(args.config)

    config = Config.load(args.config)
    setup_logger("cic", config.get("system.log_level", "INFO"), os.path.join(PROJECT_ROOT, "logs"))
    logger = logging.getLogger("cic")
    logger.info("BushQ Crypto AI headless runner started")

    if not config.validate():
        logger.error("Config validation failed")
        return 1

    if args.health:
        return health_check(config)

    return run_once(config, args.send_mode)


if __name__ == "__main__":
    raise SystemExit(main())
