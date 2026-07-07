"""Pipeline 模块 - 连接整个系统的数据流编排"""

import logging
import os
import time
import uuid
from datetime import datetime
from dateutil.parser import isoparse
from typing import Optional

from config_manager import Config
from fetchers.data_manager import DataManager
from analyzers.technical import TechnicalAnalyzer
from ai.deepseek_analyzer import DeepSeekAnalyzer
from report.report_generator import ReportGenerator, extract_report_summary_lines
from notifier.wechat_work import WeChatWorkNotifier
from storage.database import Database
from storage.repository import (
    MarketSnapshotRepo,
    KlineRepo,
    TechnicalIndicatorRepo,
    MarketStructureRepo,
    NewsRepo,
    AnalysisHistoryRepo,
    ReportRepo,
    NotificationHistoryRepo,
    SchedulerHistoryRepo,
)
from models.analysis import AnalysisData
from models.market_context import MarketContext

logger = logging.getLogger("cic.pipeline")


def _summary_only_for_mode(send_mode: str) -> Optional[bool]:
    if send_mode == "summary":
        return True
    if send_mode == "full":
        return False
    return None


class Pipeline:
    """
    核心数据流编排器。
    不做任何业务逻辑，只负责按顺序调用各模块。
    """

    def __init__(self):
        self.data_manager = DataManager()
        self.tech_analyzer = TechnicalAnalyzer()
        self.ai_analyzer = DeepSeekAnalyzer()
        self.report_generator: Optional[ReportGenerator] = None
        self.notifier = WeChatWorkNotifier()
        self.db: Optional[Database] = None
        self._config: Optional[Config] = None

    def initialize(self, config: Config) -> None:
        """初始化所有模块"""
        self._config = config

        # 数据库
        db_path = config.get("database.path", "data/crypto_intelligence.db")
        self.db = Database()
        self.db.initialize(db_path)

        # 数据采集
        self.data_manager.initialize(config)

        # AI
        self.ai_analyzer.initialize(config)

        # 报告
        report_dir = config.get("report.output_dir", "data/reports")
        self.report_generator = ReportGenerator(output_dir=report_dir)

        # 推送
        self.notifier.initialize(config)

        logger.info("Pipeline 初始化完成")

    def execute(self, send_notification: bool = True, send_mode: str = "config") -> MarketContext:
        """执行完整分析流程"""
        run_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        logger.info("========== Pipeline 开始 [run_id=%s] ==========", run_id)

        context = MarketContext(
            run_id=run_id,
            run_time=datetime.now().isoformat(),
            ai_model=self._config.get("ai.model", "") if self._config else "",
            ai_thinking_mode=self._config.get("ai.thinking_mode", "disabled") if self._config else "disabled",
        )

        try:
            # 1. 数据采集
            logger.info("[Step 1/7] 数据采集...")
            collected = self.data_manager.collect_all(self._config)
            # 合并到 context
            context.tickers = collected.tickers
            context.klines = collected.klines
            context.news = collected.news
            context.fear_greed = collected.fear_greed
            context.coin_infos = collected.coin_infos
            context.macro = collected.macro
            context.market_structure = collected.market_structure
            context.onchain_public = collected.onchain_public
            context.errors.extend(collected.errors)

            # 2. 技术分析
            logger.info("[Step 2/7] 技术分析...")
            tech_results = self.tech_analyzer.analyze_all(context.klines)
            context.tech_analyses = tech_results  # 存完整 {symbol: {timeframe: TA}}
            for symbol, tf_analyses in tech_results.items():
                if symbol not in context.analyses:
                    context.analyses[symbol] = AnalysisData(symbol=symbol)
                # 优先用日线技术分析
                if "1d" in tf_analyses:
                    context.analyses[symbol].technical = tf_analyses["1d"]
                elif tf_analyses:
                    context.analyses[symbol].technical = next(iter(tf_analyses.values()))

            # 3. AI 分析
            logger.info("[Step 3/7] AI 分析...")
            ai_result = self.ai_analyzer.analyze(context)
            if ai_result:
                for symbol in context.analyses:
                    context.analyses[symbol].ai = ai_result
                    if context.fear_greed:
                        context.analyses[symbol].fear_greed = context.fear_greed.value
            else:
                error_message = "AI 分析失败：DeepSeek 未返回可解析 JSON"
                logger.error(error_message)
                context.errors.append(error_message)

            # 4. 生成报告
            logger.info("[Step 4/7] 生成报告...")
            context.report_markdown = self.report_generator.generate(context)
            logger.info("报告生成完成，长度: %d 字符", len(context.report_markdown))

            # 5. 推送
            logger.info("[Step 5/7] 推送通知...")
            if send_notification and self._config.get("notification.enabled", True):
                push_ok = self.notifier.send_report(
                    context.report_markdown,
                    context.report_brief,
                    summary_only=_summary_only_for_mode(send_mode),
                )
            else:
                push_ok = False
                logger.info("本次未推送")

            # 6. 数据存储
            logger.info("[Step 6/7] 数据存储...")
            self._save_to_db(context, push_ok)

            # 7. 记录调度历史
            elapsed = time.time() - start_time
            SchedulerHistoryRepo.save({
                "action": "pipeline",
                "status": "success" if not context.errors else "partial",
                "duration_seconds": round(elapsed, 2),
                "run_id": run_id,
            })

            logger.info("========== Pipeline 完成 [run_id=%s] 耗时 %.1fs ==========", run_id, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("Pipeline 执行失败: %s", e, exc_info=True)
            context.errors.append(f"Pipeline 异常: {e}")
            SchedulerHistoryRepo.save({
                "action": "pipeline",
                "status": "failed",
                "duration_seconds": round(elapsed, 2),
                "error": str(e),
                "run_id": run_id,
            })

        return context

    def send_latest_report(self, send_mode: str = "config") -> bool:
        """发送最近一次生成的 Markdown 报告。"""
        if not self.report_generator:
            report_dir = self._config.get("report.output_dir", "data/reports") if self._config else "data/reports"
        else:
            report_dir = self.report_generator.output_dir

        latest = self._find_latest_report(report_dir)
        if not latest:
            logger.error("未找到历史报告，无法发送")
            return False

        with open(latest, "r", encoding="utf-8") as f:
            content = f.read()
        brief = self._build_brief_from_markdown(content, latest)
        logger.info("正在发送最近报告: %s", latest)
        return self.notifier.send_report(content, brief, summary_only=_summary_only_for_mode(send_mode))

    @staticmethod
    def _find_latest_report(report_dir: str) -> Optional[str]:
        if not os.path.isdir(report_dir):
            return None
        reports = [
            os.path.join(report_dir, name)
            for name in os.listdir(report_dir)
            if name.lower().endswith(".md")
        ]
        if not reports:
            return None
        return max(reports, key=os.path.getmtime)

    @staticmethod
    def _build_brief_from_markdown(content: str, path: str) -> str:
        first_lines = [line.strip() for line in content.splitlines() if line.strip()]
        title = first_lines[0].lstrip("# ").strip() if first_lines else "BushQ Crypto AI 报告"
        summary_lines = extract_report_summary_lines(content, max_lines=12)

        if not summary_lines:
            summary_lines = first_lines[1:8]

        brief = [f"**发送最近报告总结**", "", title, f"文件: {os.path.basename(path)}"]
        if summary_lines:
            brief.extend(["", *summary_lines])
        return "\n".join(brief)

    def _save_to_db(self, context: MarketContext, push_ok: bool) -> None:
        """保存数据到数据库"""
        def _parse_ts(ts_str: str) -> datetime:
            """将 ISO 时间字符串转为 datetime 对象"""
            if not ts_str:
                return datetime.utcnow()
            try:
                return isoparse(ts_str)
            except Exception:
                return datetime.utcnow()

        try:
            # 行情快照
            for symbol, ticker in context.tickers.items():
                if not ticker or ticker.price <= 0:
                    logger.warning("Skip invalid ticker snapshot: %s price=%s", symbol, getattr(ticker, "price", None))
                    continue
                MarketSnapshotRepo.save({
                    "symbol": symbol,
                    "timestamp": _parse_ts(ticker.timestamp),
                    "price": ticker.price,
                    "change_1h": ticker.change_1h,
                    "change_24h": ticker.change_24h,
                    "volume": ticker.volume_24h,
                    "funding_rate": ticker.funding_rate,
                    "open_interest": ticker.open_interest,
                    "fear_greed": context.fear_greed.value if context.fear_greed else None,
                })

            # K线
            for symbol, tf_klines in context.klines.items():
                for timeframe, klines in tf_klines.items():
                    records = [{
                        "symbol": k.symbol,
                        "timeframe": k.timeframe,
                        "timestamp": _parse_ts(k.timestamp),
                        "open": k.open,
                        "high": k.high,
                        "low": k.low,
                        "close": k.close,
                        "volume": k.volume,
                    } for k in klines]
                    KlineRepo.save_batch(records)

            # 技术指标
            for symbol, analysis in context.analyses.items():
                if analysis.technical:
                    tech = analysis.technical
                    TechnicalIndicatorRepo.save({
                        "symbol": symbol,
                        "timeframe": tech.timeframe,
                        "rsi": tech.rsi,
                        "trend": tech.trend,
                        "summary": tech.summary,
                    })

            # 新闻
            if context.news and context.news.items:
                news_records = [{
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "published_at": _parse_ts(item.published_at) if item.published_at else None,
                    "summary": item.summary[:200] if item.summary else "",
                    "sentiment": item.sentiment,
                    "query": context.news.query,
                } for item in context.news.items]
                NewsRepo.save_batch(news_records)

            # 分析历史
            for symbol, analysis in context.analyses.items():
                if analysis.ai:
                    AnalysisHistoryRepo.save({
                        "symbol": symbol,
                        "technical_summary": analysis.technical.summary if analysis.technical else "",
                        "ai_summary": analysis.ai.market_summary,
                        "market_phase": analysis.ai.market_phase,
                        "risk_alerts": analysis.ai.risk_alerts,
                        "confidence": analysis.ai.confidence,
                        "fear_greed": analysis.fear_greed,
                        "raw_data": analysis.ai.raw,
                    })

            # 报告
            report_id = ReportRepo.save({
                "run_id": context.run_id,
                "format": "markdown",
                "content": context.report_markdown[:5000],  # 截断存储
                "brief": context.report_brief,
                "symbols": list(context.tickers.keys()),
            })

            # 推送历史
            NotificationHistoryRepo.save({
                "channel": "wechat_work",
                "status": "success" if push_ok else "failed",
                "message_length": len(context.report_markdown),
                "report_id": report_id,
            })

            logger.info("数据存储完成")

        except Exception as e:
            logger.error("数据存储失败: %s", e)

    def close(self) -> None:
        """关闭所有资源"""
        self.data_manager.close_all()
        if self.db:
            self.db.close()
        logger.info("Pipeline 已关闭")
