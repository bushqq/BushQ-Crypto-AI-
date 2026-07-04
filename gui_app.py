#!/usr/bin/env python3
"""BushQ Crypto AI desktop GUI."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from config_manager import Config
from fetchers.data_manager import DataManager
from logger import setup_logger
from notifier.wechat_work import WeChatWorkNotifier
from pipeline.pipeline import Pipeline


APP_STYLESHEET = """
QMainWindow {
    background: #0B1020;
}
QMenuBar {
    background: #0B1020;
    color: #CBD5E1;
    padding: 6px 10px;
    border-bottom: 1px solid #1E293B;
}
QMenuBar::item {
    padding: 8px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #172033;
    color: #F8FAFC;
}
QWidget {
    color: #E2E8F0;
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #1E293B;
    background: #0F172A;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background: #0B1020;
    color: #94A3B8;
    padding: 10px 18px;
    min-width: 76px;
    border: 1px solid #1E293B;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #0F172A;
    color: #F8FAFC;
    border-top: 2px solid #F59E0B;
}
QTabBar::tab:hover {
    color: #F8FAFC;
    background: #111C30;
}
QGroupBox {
    background: #111827;
    border: 1px solid #243044;
    border-radius: 8px;
    margin-top: 14px;
    padding: 18px 14px 14px 14px;
    font-weight: 600;
    color: #F8FAFC;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #FBBF24;
}
QFrame#hero {
    background: #0F172A;
    border: 1px solid #26354E;
    border-radius: 8px;
}
QLabel#heroTitle {
    color: #F8FAFC;
    font-size: 24px;
    font-weight: 800;
}
QLabel#heroSubtitle {
    color: #94A3B8;
    font-size: 13px;
}
QLabel#statusBadge {
    background: #142034;
    border: 1px solid #2C3B55;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 8px 12px;
    font-weight: 600;
}
QLabel#mutedLabel {
    color: #94A3B8;
}
QPushButton {
    background: #172033;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 7px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1F2A44;
    border-color: #475569;
}
QPushButton:pressed {
    background: #111827;
}
QPushButton:disabled {
    color: #64748B;
    background: #111827;
    border-color: #1E293B;
}
QPushButton[variant="primary"] {
    background: #F59E0B;
    color: #0F172A;
    border-color: #FBBF24;
}
QPushButton[variant="primary"]:hover {
    background: #FBBF24;
}
QPushButton[variant="secondary"] {
    background: #20314D;
    border-color: #3B82F6;
    color: #DBEAFE;
}
QPushButton[variant="secondary"]:hover {
    background: #263A5F;
}
QCheckBox {
    spacing: 8px;
    color: #CBD5E1;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #475569;
    background: #0B1020;
}
QCheckBox::indicator:checked {
    background: #F59E0B;
    border-color: #FBBF24;
}
QProgressBar {
    background: #0B1020;
    border: 1px solid #27364F;
    border-radius: 7px;
    color: #F8FAFC;
    text-align: center;
    height: 18px;
    font-weight: 600;
}
QProgressBar::chunk {
    background: #F59E0B;
    border-radius: 6px;
}
QPlainTextEdit,
QListWidget,
QTableWidget,
QLineEdit,
QSpinBox {
    background: #0B1020;
    color: #E5E7EB;
    border: 1px solid #243044;
    border-radius: 7px;
    padding: 8px;
    selection-background-color: #334155;
    selection-color: #F8FAFC;
}
QPlainTextEdit {
    font-family: "Cascadia Mono", "Consolas";
    line-height: 1.35em;
}
QLineEdit:focus,
QSpinBox:focus,
QPlainTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {
    border-color: #F59E0B;
}
QHeaderView::section {
    background: #111827;
    color: #CBD5E1;
    border: none;
    border-bottom: 1px solid #334155;
    padding: 9px;
    font-weight: 700;
}
QTableWidget {
    gridline-color: #1E293B;
}
QTableWidget::item {
    padding: 7px;
}
QListWidget::item {
    padding: 9px 10px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #22314D;
    color: #F8FAFC;
}
QScrollBar:vertical {
    background: #0B1020;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 6px;
    min-height: 32px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class QtLogHandler(logging.Handler, QObject):
    """Forward Python logs to the GUI."""

    message = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.message.emit(self.format(record))


class TaskWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str)

    def __init__(self, task: str):
        super().__init__()
        self.task = task

    @Slot()
    def run(self) -> None:
        try:
            if self.task == "analyze_send_summary":
                result = run_pipeline(send=True, send_mode="summary")
            elif self.task == "analyze_send_full":
                result = run_pipeline(send=True, send_mode="full")
            elif self.task == "analyze_only":
                result = run_pipeline(send=False, send_mode="config")
            elif self.task == "send_latest_summary":
                result = send_latest_report(send_mode="summary")
            elif self.task == "send_latest_full":
                result = send_latest_report(send_mode="full")
            elif self.task == "health":
                result = run_health_check()
            else:
                raise ValueError(f"未知任务: {self.task}")
            self.finished.emit(self.task, result)
        except Exception as exc:
            logging.getLogger("cic.gui").exception("任务失败")
            self.failed.emit(str(exc))


def load_env() -> Dict[str, str]:
    env_path = PROJECT_ROOT / ".env"
    values: Dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.strip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def save_env(values: Dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    (PROJECT_ROOT / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_yaml_config() -> Dict[str, Any]:
    with open(PROJECT_ROOT / "config" / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_config(data: Dict[str, Any]) -> None:
    with open(PROJECT_ROOT / "config" / "config.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def load_config() -> Config:
    return Config.load(str(PROJECT_ROOT / "config" / "config.yaml"))


def run_pipeline(send: bool, send_mode: str = "config") -> Dict[str, Any]:
    config = load_config()
    pipeline = Pipeline()
    pipeline.initialize(config)
    try:
        context = pipeline.execute(send_notification=send, send_mode=send_mode)
        return {
            "report": context.report_markdown,
            "brief": context.report_brief,
            "news": context.news.items if context.news else [],
            "errors": context.errors,
        }
    finally:
        pipeline.close()


def send_latest_report(send_mode: str = "config") -> Dict[str, Any]:
    config = load_config()
    pipeline = Pipeline()
    pipeline.initialize(config)
    try:
        ok = pipeline.send_latest_report(send_mode=send_mode)
        return {"ok": ok}
    finally:
        pipeline.close()


def run_health_check() -> Dict[str, bool]:
    config = load_config()
    dm = DataManager()
    dm.initialize(config)
    try:
        return dm.health_check_all()
    finally:
        dm.close_all()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BushQ Crypto AI")
        icon_path = PROJECT_ROOT / "assets" / "bushq_crypto_ai.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1180, 780)
        self.setMinimumSize(1020, 680)
        self.active_thread: Optional[QThread] = None
        self.active_worker: Optional[TaskWorker] = None
        self.auto_runs: Dict[str, str] = {}
        self._apply_theme()

        setup_logger("cic", "INFO", str(PROJECT_ROOT / "logs"))
        self.log_handler = QtLogHandler()
        logging.getLogger("cic").addHandler(self.log_handler)
        self.log_handler.message.connect(self.append_log)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_dashboard_tab()
        self._build_report_tab()
        self._build_news_tab()
        self._build_settings_tab()
        self._build_menu()

        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(60_000)
        self.auto_timer.timeout.connect(self.check_auto_push)
        self.auto_timer.start()

        self.load_settings_into_form()
        self.refresh_reports()
        self.update_status("就绪")

    def _apply_theme(self) -> None:
        self.setStyleSheet(APP_STYLESHEET)

    def _build_menu(self) -> None:
        open_reports = QAction("打开报告目录", self)
        open_reports.triggered.connect(self.open_reports_dir)
        self.menuBar().addAction(open_reports)

    def _build_dashboard_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(18)

        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(6)
        title = QLabel("BushQ Crypto AI")
        title.setObjectName("heroTitle")
        subtitle = QLabel("合约行情、宏观数据、新闻与 AI 分析的自动化情报主控台")
        subtitle.setObjectName("heroSubtitle")
        hero_copy.addWidget(title)
        hero_copy.addWidget(subtitle)
        hero_layout.addLayout(hero_copy, 1)

        self.market_scope_label = QLabel("BTC / ETH / SOL / LTC / DOGE · OKX SWAP")
        self.market_scope_label.setObjectName("mutedLabel")
        hero_layout.addWidget(self.market_scope_label)
        layout.addWidget(hero)

        status_box = QGroupBox("状态")
        status_layout = QHBoxLayout(status_box)
        status_layout.setSpacing(12)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusBadge")
        self.last_run_label = QLabel("上次运行：-")
        self.last_run_label.setObjectName("mutedLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumWidth(300)
        self.auto_push_checkbox = QCheckBox("开启自动推送")
        self.auto_push_checkbox.stateChanged.connect(self.on_auto_push_changed)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.addStretch()
        status_layout.addWidget(self.last_run_label)
        status_layout.addWidget(self.auto_push_checkbox)
        layout.addWidget(status_box)

        button_box = QGroupBox("操作")
        button_layout = QHBoxLayout(button_box)
        button_layout.setSpacing(10)
        self.btn_analyze_send_summary = QPushButton("分析并发总结")
        self.btn_analyze_send_full = QPushButton("分析并发完整")
        self.btn_analyze_only = QPushButton("重新分析但不发送")
        self.btn_send_latest_summary = QPushButton("发送最近总结")
        self.btn_send_latest_full = QPushButton("发送最近完整")
        self.btn_health = QPushButton("健康检查")
        self.btn_reports = QPushButton("打开报告目录")
        self.btn_analyze_send_summary.setProperty("variant", "primary")
        self.btn_analyze_send_full.setProperty("variant", "secondary")
        for button in [
            self.btn_analyze_send_summary,
            self.btn_analyze_send_full,
            self.btn_analyze_only,
            self.btn_send_latest_summary,
            self.btn_send_latest_full,
            self.btn_health,
            self.btn_reports,
        ]:
            button.setMinimumHeight(42)
            button_layout.addWidget(button)
        self.btn_analyze_send_summary.clicked.connect(lambda: self.start_task("analyze_send_summary"))
        self.btn_analyze_send_full.clicked.connect(lambda: self.start_task("analyze_send_full"))
        self.btn_analyze_only.clicked.connect(lambda: self.start_task("analyze_only"))
        self.btn_send_latest_summary.clicked.connect(lambda: self.start_task("send_latest_summary"))
        self.btn_send_latest_full.clicked.connect(lambda: self.start_task("send_latest_full"))
        self.btn_health.clicked.connect(lambda: self.start_task("health"))
        self.btn_reports.clicked.connect(self.open_reports_dir)
        layout.addWidget(button_box)

        log_box = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(12, 16, 12, 12)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_box, 1)
        self.tabs.addTab(tab, "主控台")

    def _build_report_tab(self) -> None:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(10)
        self.report_list = QListWidget()
        self.report_list.currentTextChanged.connect(self.load_selected_report)
        refresh = QPushButton("刷新历史报告")
        refresh.clicked.connect(self.refresh_reports)
        left.addWidget(QLabel("历史报告"))
        left.addWidget(self.report_list)
        left.addWidget(refresh)
        layout.addLayout(left, 1)

        self.report_view = QPlainTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setFont(QFont("Cascadia Mono", 10))
        layout.addWidget(self.report_view, 3)
        self.tabs.addTab(tab, "报告")

    def _build_news_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        self.news_table = QTableWidget(0, 4)
        self.news_table.setHorizontalHeaderLabels(["来源", "标题", "时间", "链接"])
        self.news_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.news_table)
        self.tabs.addTab(tab, "新闻")

    def _build_settings_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        form_box = QGroupBox("配置")
        form = QFormLayout(form_box)
        self.deepseek_key = QLineEdit()
        self.tavily_key = QLineEdit()
        self.wechat_webhook = QLineEdit()
        for field in [self.deepseek_key, self.tavily_key, self.wechat_webhook]:
            field.setEchoMode(QLineEdit.Password)
        self.deepseek_model = QLineEdit()
        self.proxy = QLineEdit()
        self.news_total = QSpinBox()
        self.news_total.setRange(20, 200)
        self.symbols = QLineEdit()
        form.addRow("DeepSeek Key", self.deepseek_key)
        form.addRow("Tavily Key", self.tavily_key)
        form.addRow("企业微信 Webhook", self.wechat_webhook)
        form.addRow("DeepSeek 模型", self.deepseek_model)
        form.addRow("代理地址", self.proxy)
        form.addRow("新闻总量", self.news_total)
        form.addRow("币种列表", self.symbols)
        layout.addWidget(form_box)

        prompt_box = QGroupBox("AI Prompt")
        prompt_layout = QVBoxLayout(prompt_box)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumHeight(220)
        prompt_layout.addWidget(self.prompt_edit)
        layout.addWidget(prompt_box, 1)

        buttons = QHBoxLayout()
        save = QPushButton("保存设置")
        save.setProperty("variant", "primary")
        reveal = QCheckBox("显示密钥")
        save.clicked.connect(self.save_settings)
        reveal.stateChanged.connect(self.toggle_secret_visibility)
        buttons.addWidget(save)
        buttons.addWidget(reveal)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.tabs.addTab(tab, "设置")

    def start_task(self, task: str) -> None:
        if self._task_is_running():
            QMessageBox.information(self, "任务运行中", "已有任务正在运行，请稍后。")
            return
        self.append_log(f"按钮已点击：{self._task_label(task)}")
        self.set_buttons_enabled(False)
        self.set_progress(3, "启动任务")
        self.update_status(f"运行中：{self._task_label(task)}")
        self.active_thread = QThread()
        self.active_worker = TaskWorker(task)
        self.active_worker.moveToThread(self.active_thread)
        self.active_thread.started.connect(self.active_worker.run)
        self.active_worker.finished.connect(self.on_task_finished)
        self.active_worker.failed.connect(self.on_task_failed)
        self.active_worker.finished.connect(self.active_thread.quit)
        self.active_worker.failed.connect(self.active_thread.quit)
        self.active_thread.finished.connect(self.active_worker.deleteLater)
        self.active_thread.finished.connect(self.active_thread.deleteLater)
        self.active_thread.finished.connect(self.clear_active_task)
        self.active_thread.start()

    def _task_is_running(self) -> bool:
        """Safely check task state; Qt may have deleted the wrapped QThread."""
        if not self.active_thread:
            return False
        try:
            return self.active_thread.isRunning()
        except RuntimeError:
            self.active_thread = None
            self.active_worker = None
            return False

    @staticmethod
    def _task_label(task: str) -> str:
        labels = {
            "analyze_send_summary": "分析并发总结",
            "analyze_send_full": "分析并发完整",
            "analyze_only": "重新分析但不发送",
            "send_latest_summary": "发送最近总结",
            "send_latest_full": "发送最近完整",
            "health": "健康检查",
        }
        return labels.get(task, task)

    @Slot()
    def clear_active_task(self) -> None:
        self.active_thread = None
        self.active_worker = None

    @Slot(str, object)
    def on_task_finished(self, task: str, result: object) -> None:
        self.set_buttons_enabled(True)
        self.set_progress(100, "完成")
        self.last_run_label.setText(f"上次运行：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.update_status("就绪")
        self.append_log(f"任务完成：{self._task_label(task)}")
        if task in {"analyze_send_summary", "analyze_send_full", "analyze_only"} and isinstance(result, dict):
            self.report_view.setPlainText(result.get("report", ""))
            self.populate_news(result.get("news", []))
            self.refresh_reports()
            self.tabs.setCurrentIndex(1)
        elif task in {"send_latest_summary", "send_latest_full"}:
            ok = bool(result.get("ok")) if isinstance(result, dict) else False
            self.append_log(f"{self._task_label(task)}：" + ("成功" if ok else "失败"))
            QMessageBox.information(self, self._task_label(task), "发送成功" if ok else "发送失败")
        elif task == "health":
            lines = [f"{name}: {'OK' if ok else 'UNAVAILABLE'}" for name, ok in dict(result).items()]
            self.append_log("健康检查结果：\n" + "\n".join(lines))
            QMessageBox.information(self, "健康检查", "\n".join(lines))

    @Slot(str)
    def on_task_failed(self, message: str) -> None:
        self.set_buttons_enabled(True)
        self.set_progress(0, "失败")
        self.update_status("失败")
        self.append_log(f"任务失败：{message}")
        QMessageBox.critical(self, "任务失败", message)

    def set_buttons_enabled(self, enabled: bool) -> None:
        for button in [
            self.btn_analyze_send_summary,
            self.btn_analyze_send_full,
            self.btn_analyze_only,
            self.btn_send_latest_summary,
            self.btn_send_latest_full,
            self.btn_health,
            self.btn_reports,
        ]:
            button.setEnabled(enabled)

    def update_status(self, text: str) -> None:
        self.status_label.setText(f"状态：{text}")

    @Slot(str)
    def append_log(self, line: str) -> None:
        self.log_text.appendPlainText(line)
        self.update_progress_from_log(line)

    def set_progress(self, value: int, label: str = "") -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{value}% {label}".strip())

    def set_busy_progress(self, label: str) -> None:
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat(label)

    def update_progress_from_log(self, line: str) -> None:
        if "[Step 1/7]" in line:
            self.set_progress(10, "数据采集")
        elif "[Step 2/7]" in line:
            self.set_progress(35, "技术分析")
        elif "[Step 3/7]" in line:
            self.set_progress(45, "准备 AI 分析")
        elif "开始 AI 分析" in line:
            self.set_busy_progress("AI 分析中...")
        elif "尝试自动修复 JSON" in line:
            self.set_busy_progress("AI JSON 修复中...")
        elif "分析完成" in line and "DeepSeek" in line:
            self.set_progress(70, "AI 分析完成")
        elif "[Step 4/7]" in line:
            self.set_progress(78, "生成报告")
        elif "[Step 5/7]" in line:
            self.set_progress(86, "推送通知")
        elif "[Step 6/7]" in line:
            self.set_progress(93, "保存数据")
        elif "Pipeline 完成" in line:
            self.set_progress(100, "完成")

    def populate_news(self, items: List[Any]) -> None:
        self.news_table.setRowCount(0)
        for item in items:
            row = self.news_table.rowCount()
            self.news_table.insertRow(row)
            self.news_table.setItem(row, 0, QTableWidgetItem(getattr(item, "source", "")))
            self.news_table.setItem(row, 1, QTableWidgetItem(getattr(item, "title", "")))
            self.news_table.setItem(row, 2, QTableWidgetItem(getattr(item, "published_at", "")))
            self.news_table.setItem(row, 3, QTableWidgetItem(getattr(item, "url", "")))
        self.news_table.resizeColumnsToContents()

    def refresh_reports(self) -> None:
        self.report_list.clear()
        report_dir = PROJECT_ROOT / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        reports = sorted(report_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        for report in reports:
            self.report_list.addItem(report.name)
        if reports:
            self.report_list.setCurrentRow(0)

    def load_selected_report(self, name: str) -> None:
        if not name:
            return
        path = PROJECT_ROOT / "data" / "reports" / name
        if path.exists():
            self.report_view.setPlainText(path.read_text(encoding="utf-8"))

    def open_reports_dir(self) -> None:
        report_dir = PROJECT_ROOT / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        self.append_log(f"打开报告目录：{report_dir}")
        os.startfile(report_dir)

    def toggle_secret_visibility(self, state: int) -> None:
        mode = QLineEdit.Normal if state == Qt.Checked else QLineEdit.Password
        for field in [self.deepseek_key, self.tavily_key, self.wechat_webhook]:
            field.setEchoMode(mode)

    def load_settings_into_form(self) -> None:
        env = load_env()
        cfg = load_yaml_config()
        self.deepseek_key.setText(env.get("DEEPSEEK_API_KEY", ""))
        self.tavily_key.setText(env.get("TAVILY_API_KEY", ""))
        self.wechat_webhook.setText(env.get("WECHAT_WORK_WEBHOOK_URL", ""))
        self.deepseek_model.setText(env.get("DEEPSEEK_MODEL", cfg.get("ai", {}).get("model", "deepseek-v4-pro")))
        self.proxy.setText(cfg.get("exchange", {}).get("proxy", ""))
        self.news_total.setValue(int(cfg.get("news", {}).get("total_limit", 80)))
        self.symbols.setText(", ".join(cfg.get("symbols", [])))
        self.auto_push_checkbox.setChecked(bool(cfg.get("scheduler", {}).get("auto_push_enabled", False)))
        prompt_path = PROJECT_ROOT / cfg.get("ai", {}).get("prompt_template", "templates/prompts/daily_analysis.md")
        if prompt_path.exists():
            self.prompt_edit.setPlainText(prompt_path.read_text(encoding="utf-8"))

    def save_settings(self) -> None:
        env = load_env()
        env["DEEPSEEK_API_KEY"] = self.deepseek_key.text().strip()
        env["TAVILY_API_KEY"] = self.tavily_key.text().strip()
        env["WECHAT_WORK_WEBHOOK_URL"] = self.wechat_webhook.text().strip()
        env["DEEPSEEK_MODEL"] = self.deepseek_model.text().strip() or "deepseek-v4-pro"
        env.setdefault("DISABLE_INTERVAL_SCHEDULE", "true")
        save_env(env)

        cfg = load_yaml_config()
        cfg.setdefault("exchange", {})["proxy"] = self.proxy.text().strip()
        cfg.setdefault("news", {})["total_limit"] = int(self.news_total.value())
        cfg["symbols"] = [s.strip() for s in self.symbols.text().split(",") if s.strip()]
        cfg.setdefault("scheduler", {})["auto_push_enabled"] = self.auto_push_checkbox.isChecked()
        save_yaml_config(cfg)

        prompt_path = PROJECT_ROOT / cfg.get("ai", {}).get("prompt_template", "templates/prompts/daily_analysis.md")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(self.prompt_edit.toPlainText(), encoding="utf-8")
        QMessageBox.information(self, "设置", "保存成功")

    def on_auto_push_changed(self, *_args) -> None:
        cfg = load_yaml_config()
        cfg.setdefault("scheduler", {})["auto_push_enabled"] = self.auto_push_checkbox.isChecked()
        save_yaml_config(cfg)

    def check_auto_push(self) -> None:
        if not self.auto_push_checkbox.isChecked():
            return
        if self.active_thread and self.active_thread.isRunning():
            return
        cfg = load_yaml_config()
        markets = cfg.get("market_reminder", {}).get("markets", [])
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current = now.strftime("%H:%M")
        for market in markets:
            name = market.get("name", "market")
            remind_time = market.get("remind_time")
            if current == remind_time and self.auto_runs.get(name) != today:
                self.auto_runs[name] = today
                self.append_log(f"自动推送触发：{name} {remind_time}")
                self.start_task("analyze_send_full")
                break


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
