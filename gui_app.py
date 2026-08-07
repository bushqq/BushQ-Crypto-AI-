#!/usr/bin/env python3
"""BushQ Crypto AI desktop GUI."""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from PySide6.QtCore import QEvent, QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
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
QScrollArea,
QScrollArea QWidget#qt_scrollarea_viewport,
QWidget#settingsContent {
    background: #0F172A;
    border: none;
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
QLabel#settingsSectionLabel {
    color: #CBD5E1;
    font-weight: 600;
    padding-top: 2px;
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
QSpinBox,
QDoubleSpinBox {
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
QDoubleSpinBox:focus,
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
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
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
            "trade_plans": list(context.trade_plans.values()),
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
    SETTINGS_BREAKPOINT = 900

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BushQ Crypto AI")
        icon_path = PROJECT_ROOT / "assets" / "bushq_crypto_ai.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1180, 780)
        self.setMinimumSize(720, 560)
        self.active_thread: Optional[QThread] = None
        self.active_worker: Optional[TaskWorker] = None
        self.auto_runs: Dict[str, str] = {}
        self._loading_settings = False
        self._apply_theme()

        setup_logger("cic", "INFO", str(PROJECT_ROOT / "logs"))
        self.log_handler = QtLogHandler()
        logging.getLogger("cic").addHandler(self.log_handler)
        self.log_handler.message.connect(self.append_log)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_dashboard_tab()
        self._build_report_tab()
        self._build_trade_plan_tab()
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
        self.ai_mode_label = QLabel("AI：-")
        self.ai_mode_label.setObjectName("mutedLabel")
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
        status_layout.addWidget(self.ai_mode_label)
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

    def _build_trade_plan_tab(self) -> None:
        tab = QWidget()
        self.trade_plan_tab = tab
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        self.trade_plan_table = QTableWidget(0, 11)
        self.trade_plan_table.setHorizontalHeaderLabels(
            ["标的", "结论", "入场区间", "参考入场", "止损", "失效 / 强平", "TP1", "TP2", "TP3", "仓位 / 杠杆", "净盈亏比"]
        )
        self.trade_plan_table.horizontalHeader().setStretchLastSection(True)
        self.trade_plan_table.setColumnWidth(0, 145)
        self.trade_plan_table.setColumnWidth(1, 85)
        self.trade_plan_table.setColumnWidth(2, 150)
        for column in range(3, 9):
            self.trade_plan_table.setColumnWidth(column, 95)
        self.trade_plan_table.setColumnWidth(5, 145)
        self.trade_plan_table.setColumnWidth(9, 150)
        layout.addWidget(self.trade_plan_table)
        self.tabs.addTab(tab, "交易计划")

    def _build_settings_tab(self) -> None:
        tab = QWidget()
        self.settings_tab = tab
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setObjectName("settingsScrollArea")
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.settings_scroll.setFrameShape(QFrame.NoFrame)
        self.settings_scroll.viewport().installEventFilter(self)

        settings_content = QWidget()
        settings_content.setObjectName("settingsContent")
        content_layout = QVBoxLayout(settings_content)
        content_layout.setContentsMargins(20, 18, 20, 24)
        content_layout.setSpacing(16)
        self.settings_grid = QGridLayout()
        self.settings_grid.setContentsMargins(0, 0, 0, 0)
        self.settings_grid.setHorizontalSpacing(16)
        self.settings_grid.setVerticalSpacing(16)

        self.interface_settings_group = QGroupBox("接口配置")
        self.interface_settings_group.setObjectName("interfaceSettingsGroup")
        interface_form = QFormLayout(self.interface_settings_group)
        self._configure_settings_form(interface_form)
        self.deepseek_key = QLineEdit()
        self.tavily_key = QLineEdit()
        self.wechat_webhook = QLineEdit()
        for field in [self.deepseek_key, self.tavily_key, self.wechat_webhook]:
            field.setEchoMode(QLineEdit.Password)
        self.deepseek_model = QLineEdit()
        self.proxy = QLineEdit()
        for field in [self.deepseek_key, self.tavily_key, self.wechat_webhook, self.deepseek_model, self.proxy]:
            self._configure_text_input(field)
        self.secret_toggle_button = QPushButton("显示密钥")
        self.secret_toggle_button.setCheckable(True)
        self.secret_toggle_button.setMinimumHeight(36)
        self.secret_toggle_button.setMaximumWidth(112)
        self.secret_toggle_button.toggled.connect(self.toggle_secret_visibility)
        self._add_settings_row(interface_form, "DeepSeek Key", self.deepseek_key)
        self._add_settings_row(interface_form, "Tavily Key", self.tavily_key)
        self._add_settings_row(interface_form, "企业微信 Webhook", self.wechat_webhook)
        self._add_settings_row(interface_form, "DeepSeek 模型", self.deepseek_model)
        self._add_settings_row(interface_form, "代理地址", self.proxy)
        self._add_settings_row(interface_form, "", self.secret_toggle_button)

        self.analysis_settings_group = QGroupBox("分析设置")
        self.analysis_settings_group.setObjectName("analysisSettingsGroup")
        analysis_layout = QVBoxLayout(self.analysis_settings_group)
        analysis_layout.setContentsMargins(14, 18, 14, 14)
        analysis_layout.setSpacing(12)
        analysis_form = QFormLayout()
        self._configure_settings_form(analysis_form)
        self.deep_thinking_checkbox = QCheckBox("深度思考模式（仅本地手动分析）")
        self.news_total = QSpinBox()
        self.news_total.setRange(20, 200)
        self.news_total.setSingleStep(10)
        self.news_total.setSuffix(" 条")
        self.symbols = QPlainTextEdit()
        self.symbols.setPlaceholderText("每行一个，例如 BTC-USDT-SWAP")
        self.symbols.setMinimumHeight(96)
        self.symbols.setMaximumHeight(128)
        self._configure_numeric_input(self.news_total)
        self._add_settings_row(analysis_form, "AI 模式", self.deep_thinking_checkbox)
        self._add_settings_row(analysis_form, "新闻总量", self.news_total)
        self._add_settings_row(analysis_form, "币种列表", self.symbols)
        analysis_layout.addLayout(analysis_form)
        prompt_label = QLabel("分析提示词")
        prompt_label.setObjectName("settingsSectionLabel")
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumHeight(180)
        analysis_layout.addWidget(prompt_label)
        analysis_layout.addWidget(self.prompt_edit)

        self.risk_settings_group = QGroupBox("交易风控")
        self.risk_settings_group.setObjectName("riskSettingsGroup")
        risk_form = QFormLayout(self.risk_settings_group)
        self._configure_settings_form(risk_form)
        self.trade_plan_enabled = QCheckBox("生成研究型交易计划")
        self.risk_capital = QDoubleSpinBox()
        self.risk_capital.setRange(100, 100_000_000)
        self.risk_capital.setDecimals(2)
        self.risk_capital.setSingleStep(100)
        self.risk_capital.setSuffix(" USDT")
        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.01, 10)
        self.risk_per_trade.setDecimals(2)
        self.risk_per_trade.setSingleStep(0.1)
        self.risk_per_trade.setSuffix(" %")
        self.margin_budget = QDoubleSpinBox()
        self.margin_budget.setRange(0.1, 100)
        self.margin_budget.setDecimals(1)
        self.margin_budget.setSingleStep(1)
        self.margin_budget.setSuffix(" %")
        self.max_leverage = QSpinBox()
        self.max_leverage.setRange(1, 20)
        self.max_leverage.setSingleStep(1)
        self.max_leverage.setSuffix(" 倍")
        self.min_reward_risk = QDoubleSpinBox()
        self.min_reward_risk.setRange(1.0, 10.0)
        self.min_reward_risk.setDecimals(2)
        self.min_reward_risk.setSingleStep(0.1)
        self.min_reward_risk.setSuffix(" : 1")
        for field in [self.risk_capital, self.risk_per_trade, self.margin_budget, self.max_leverage, self.min_reward_risk]:
            self._configure_numeric_input(field)
        self._add_settings_row(risk_form, "启用交易计划", self.trade_plan_enabled)
        self._add_settings_row(risk_form, "风险本金", self.risk_capital)
        self._add_settings_row(risk_form, "单笔风险上限", self.risk_per_trade)
        self._add_settings_row(risk_form, "保证金预算", self.margin_budget)
        self._add_settings_row(risk_form, "杠杆上限", self.max_leverage)
        self._add_settings_row(risk_form, "最低净盈亏比", self.min_reward_risk)

        content_layout.addLayout(self.settings_grid)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.save_settings_button = QPushButton("保存设置")
        self.save_settings_button.setProperty("variant", "primary")
        self.save_settings_button.setMinimumHeight(42)
        self.save_settings_button.clicked.connect(self.save_settings)
        self.deep_thinking_checkbox.stateChanged.connect(self.on_deep_thinking_changed)
        buttons.addWidget(self.save_settings_button)
        buttons.addStretch()
        content_layout.addLayout(buttons)
        content_layout.addStretch()

        self.settings_scroll.setWidget(settings_content)
        tab_layout.addWidget(self.settings_scroll)
        self._settings_layout_mode = ""
        self._update_settings_layout(force=True)
        self.tabs.addTab(tab, "设置")

    @staticmethod
    def _configure_settings_form(form: QFormLayout) -> None:
        form.setContentsMargins(14, 18, 14, 14)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)

    @staticmethod
    def _add_settings_row(form: QFormLayout, text: str, field: QWidget) -> None:
        label = QLabel(text)
        label.setFixedWidth(126)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.addRow(label, field)

    @staticmethod
    def _configure_text_input(field: QLineEdit) -> None:
        field.setMinimumHeight(40)
        field.setMaximumWidth(520)

    @staticmethod
    def _configure_numeric_input(field: QWidget) -> None:
        field.setMinimumHeight(40)
        field.setMaximumWidth(240)

    @property
    def settings_layout_mode(self) -> str:
        return self._settings_layout_mode

    def _update_settings_layout(self, force: bool = False) -> None:
        if not hasattr(self, "settings_scroll"):
            return
        mode = "double" if self.settings_scroll.viewport().width() >= self.SETTINGS_BREAKPOINT else "single"
        if not force and mode == self._settings_layout_mode:
            return
        for group in [self.interface_settings_group, self.analysis_settings_group, self.risk_settings_group]:
            self.settings_grid.removeWidget(group)
        if mode == "double":
            self.settings_grid.addWidget(self.interface_settings_group, 0, 0, Qt.AlignTop)
            self.settings_grid.addWidget(self.analysis_settings_group, 0, 1, Qt.AlignTop)
            self.settings_grid.addWidget(self.risk_settings_group, 1, 0, 1, 2, Qt.AlignTop)
            self.settings_grid.setColumnStretch(0, 1)
            self.settings_grid.setColumnStretch(1, 1)
        else:
            self.settings_grid.addWidget(self.interface_settings_group, 0, 0)
            self.settings_grid.addWidget(self.analysis_settings_group, 1, 0)
            self.settings_grid.addWidget(self.risk_settings_group, 2, 0)
            self.settings_grid.setColumnStretch(0, 1)
            self.settings_grid.setColumnStretch(1, 0)
        self._settings_layout_mode = mode

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if hasattr(self, "settings_scroll") and watched is self.settings_scroll.viewport() and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._update_settings_layout)
        return super().eventFilter(watched, event)

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
            self.populate_trade_plans(result.get("trade_plans", []))
            self.refresh_reports()
            self.tabs.setCurrentWidget(self.trade_plan_tab)
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

    def populate_trade_plans(self, plans: List[Any]) -> None:
        self.trade_plan_table.setRowCount(0)
        for plan in plans:
            row = self.trade_plan_table.rowCount()
            self.trade_plan_table.insertRow(row)
            targets = list(getattr(plan, "take_profits", []))
            values = [
                getattr(plan, "symbol", ""),
                getattr(plan, "conclusion", ""),
                self._plan_range(plan),
                self._plan_price(getattr(plan, "reference_entry", None)),
                self._plan_price(getattr(plan, "stop_loss", None)),
                f"{self._plan_price(getattr(plan, 'chase_invalidation', None))} / {self._plan_price(getattr(plan, 'liquidation_price', None))}",
                self._plan_price(getattr(targets[0], "price", None)) if len(targets) > 0 else "-",
                self._plan_price(getattr(targets[1], "price", None)) if len(targets) > 1 else "-",
                self._plan_price(getattr(targets[2], "price", None)) if len(targets) > 2 else "-",
                f"{getattr(plan, 'notional_usdt', 0):.2f} USDT / {getattr(plan, 'leverage', 1)}x",
                f"{getattr(plan, 'net_reward_risk', 0):.2f}",
            ]
            if getattr(plan, "conclusion", "") == "NO_TRADE":
                values[2] = getattr(plan, "reason", "NO_TRADE")
            for column, value in enumerate(values):
                self.trade_plan_table.setItem(row, column, QTableWidgetItem(str(value)))

    @staticmethod
    def _plan_price(value: Optional[float]) -> str:
        if value is None:
            return "-"
        if value >= 1000:
            return f"{value:.1f}"
        if value >= 1:
            return f"{value:.2f}"
        return f"{value:.6f}"

    @classmethod
    def _plan_range(cls, plan: Any) -> str:
        return f"{cls._plan_price(getattr(plan, 'entry_low', None))} - {cls._plan_price(getattr(plan, 'entry_high', None))}"

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

    def toggle_secret_visibility(self, visible: bool) -> None:
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        for field in [self.deepseek_key, self.tavily_key, self.wechat_webhook]:
            field.setEchoMode(mode)
        self.secret_toggle_button.setText("隐藏密钥" if visible else "显示密钥")

    def load_settings_into_form(self) -> None:
        self._loading_settings = True
        env = load_env()
        cfg = load_yaml_config()
        self.deepseek_key.setText(env.get("DEEPSEEK_API_KEY", ""))
        self.tavily_key.setText(env.get("TAVILY_API_KEY", ""))
        self.wechat_webhook.setText(env.get("WECHAT_WORK_WEBHOOK_URL", ""))
        self.deepseek_model.setText(env.get("DEEPSEEK_MODEL", cfg.get("ai", {}).get("model", "deepseek-v4-pro")))
        self.deep_thinking_checkbox.setChecked(str(cfg.get("ai", {}).get("thinking_mode", "disabled")).lower() == "enabled")
        self.proxy.setText(cfg.get("exchange", {}).get("proxy", ""))
        self.news_total.setValue(int(cfg.get("news", {}).get("total_limit", 80)))
        self.symbols.setPlainText("\n".join(cfg.get("symbols", [])))
        trade_plan = cfg.get("trade_plan", {})
        self.trade_plan_enabled.setChecked(bool(trade_plan.get("enabled", True)))
        self.risk_capital.setValue(float(trade_plan.get("risk_capital_usdt", 1000)))
        self.risk_per_trade.setValue(float(trade_plan.get("risk_per_trade_percent", 1.0)))
        self.margin_budget.setValue(float(trade_plan.get("margin_budget_percent", 20.0)))
        self.max_leverage.setValue(int(trade_plan.get("max_leverage", 3)))
        self.min_reward_risk.setValue(float(trade_plan.get("min_reward_risk", 1.8)))
        self.auto_push_checkbox.setChecked(bool(cfg.get("scheduler", {}).get("auto_push_enabled", False)))
        self.update_ai_mode_label()
        prompt_path = PROJECT_ROOT / cfg.get("ai", {}).get("prompt_template", "templates/prompts/daily_analysis.md")
        if prompt_path.exists():
            self.prompt_edit.setPlainText(prompt_path.read_text(encoding="utf-8"))
        self._loading_settings = False

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
        cfg.setdefault("ai", {})["thinking_mode"] = "enabled" if self.deep_thinking_checkbox.isChecked() else "disabled"
        cfg.setdefault("news", {})["total_limit"] = int(self.news_total.value())
        cfg["symbols"] = [s for s in re.split(r"[,，;；\s]+", self.symbols.toPlainText().strip()) if s]
        trade_plan = cfg.setdefault("trade_plan", {})
        trade_plan["enabled"] = self.trade_plan_enabled.isChecked()
        trade_plan["risk_capital_usdt"] = float(self.risk_capital.value())
        trade_plan["risk_per_trade_percent"] = float(self.risk_per_trade.value())
        trade_plan["margin_budget_percent"] = float(self.margin_budget.value())
        trade_plan["max_leverage"] = int(self.max_leverage.value())
        trade_plan["min_reward_risk"] = float(self.min_reward_risk.value())
        cfg.setdefault("scheduler", {})["auto_push_enabled"] = self.auto_push_checkbox.isChecked()
        save_yaml_config(cfg)

        prompt_path = PROJECT_ROOT / cfg.get("ai", {}).get("prompt_template", "templates/prompts/daily_analysis.md")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(self.prompt_edit.toPlainText(), encoding="utf-8")
        self.update_ai_mode_label()
        QMessageBox.information(self, "设置", "保存成功")

    def update_ai_mode_label(self) -> None:
        cfg = load_yaml_config()
        env = load_env()
        model = env.get("DEEPSEEK_MODEL") or cfg.get("ai", {}).get("model", "-")
        thinking = str(cfg.get("ai", {}).get("thinking_mode", "disabled")).lower()
        mode = "深度思考模式" if thinking == "enabled" else "稳定 JSON 模式"
        self.ai_mode_label.setText(f"AI：{model} · {mode}")

    def on_auto_push_changed(self, *_args) -> None:
        cfg = load_yaml_config()
        cfg.setdefault("scheduler", {})["auto_push_enabled"] = self.auto_push_checkbox.isChecked()
        save_yaml_config(cfg)

    def on_deep_thinking_changed(self, *_args) -> None:
        if self._loading_settings:
            return
        cfg = load_yaml_config()
        cfg.setdefault("ai", {})["thinking_mode"] = "enabled" if self.deep_thinking_checkbox.isChecked() else "disabled"
        save_yaml_config(cfg)
        self.update_ai_mode_label()

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
