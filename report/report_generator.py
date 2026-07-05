"""报告生成模块 - Markdown 日报"""

import os
import logging
from datetime import datetime
from typing import Any, Optional

from models.market_context import MarketContext
from models.analysis import AIAnalysis

logger = logging.getLogger("cic.report")


# 市场阶段中文映射
PHASE_MAP = {
    "accumulation": "积累期",
    "markup": "上涨期",
    "distribution": "分配期",
    "markdown": "下跌期",
    "unknown": "无法判断",
    "rebound": "反弹修复",
    "consolidation": "震荡整理",
    "pullback": "回调",
}

# 恐惧贪婪中文映射
FG_CLASSIFICATION_MAP = {
    "Extreme Fear": "极度恐惧",
    "Fear": "恐惧",
    "Neutral": "中性",
    "Greed": "贪婪",
    "Extreme Greed": "极度贪婪",
}

VALUE_CN_MAP = {
    "unknown": "无法判断",
    "missing": "缺失",
    "available": "可用",
    "partial": "部分可用",
    "insufficient": "不足",
    "skipped": "未接入",
    "public_proxy": "公开代理数据",
    "high": "高",
    "medium": "中",
    "low": "低",
    "critical": "严重",
    "neutral": "中性",
    "bullish": "利多",
    "bearish": "利空",
    "positive": "偏正面",
    "negative": "偏负面",
    "risk-on": "风险偏好",
    "risk-off": "风险规避",
    "accumulation": "吸筹阶段",
    "markup": "上涨阶段",
    "distribution": "派发阶段",
    "markdown": "下跌阶段",
    "rebound": "反弹修复",
    "consolidation": "震荡整理",
    "pullback": "回调",
    "downtrend": "下跌趋势",
    "uptrend": "上涨趋势",
    "range": "区间震荡",
    "watch only": "仅观察",
    "wait for pullback": "等待回调",
    "wait for breakout": "等待突破确认",
    "light probe": "轻仓试探",
    "hold existing only": "仅持有已有仓位",
    "reduce risk": "降低风险敞口",
    "no position": "不建议建立仓位",
    "flow in": "资金流入",
    "flow out": "资金流出",
    "inflow": "资金流入",
    "outflow": "资金流出",
    "sideways": "观望",
    "risk on": "风险偏好",
    "risk off": "风险规避",
    "watch_only": "仅观察",
    "wait_for_pullback": "等待回调",
    "wait_for_breakout": "等待突破确认",
    "light_probe": "轻仓试探",
    "hold_existing_only": "仅持有已有仓位",
    "reduce_risk": "降低风险敞口",
    "no_position": "不建议建立仓位",
    "technical": "技术面风险",
    "positioning": "仓位/杠杆风险",
    "sentiment_divergence": "情绪背离风险",
    "sentiment divergence": "情绪背离风险",
    "macro_uncertainty": "宏观不确定性风险",
    "macro uncertainty": "宏观不确定性风险",
    "fund_flow": "资金流风险",
    "fund flow": "资金流风险",
    "liquidity": "流动性风险",
    "leverage": "杠杆风险",
    "news": "新闻事件风险",
    "regulatory": "监管风险",
    "onchain": "链上风险",
    "on_chain": "链上风险",
    "on chain": "链上风险",
}

KEY_CN_MAP = {
    "risk_mode": "风险模式",
    "summary": "总结",
    "evidence": "依据",
    "data_gap": "数据缺口",
    "data_gaps": "数据缺口",
    "status": "状态",
    "direction": "方向",
    "strength": "强度",
    "leverage_state": "杠杆状态",
    "impact": "影响",
    "fear_greed": "恐惧贪婪",
    "social": "社交情绪",
    "overall": "综合判断",
    "source": "来源",
    "url": "链接",
    "published_at": "发布时间",
    "watch_data": "观察数据",
    "data_to_watch": "观察数据",
    "level": "等级",
    "type": "类型",
    "topic": "主题",
    "title": "标题",
    "event": "事件",
    "duration": "持续时间",
    "reason": "原因",
    "state": "状态",
    "technical_summary": "技术总结",
    "risk": "风险",
    "entry_zone": "观察入场区域",
    "near_support": "支撑附近",
    "breakout_above": "突破确认",
    "invalid_below": "失效位置",
    "condition": "观察条件",
    "warnings": "提示",
    "unsupported_claims_removed": "已移除无依据结论",
    "score_evidence": "评分依据",
    "market_score": "市场评分",
    "bullish_score": "多头评分",
    "bearish_score": "空头评分",
    "trend_strength": "趋势强度",
    "dxy": "美元指数",
    "treasury_yields": "美债收益率",
    "total_market_cap_usd": "加密总市值",
    "total_volume_24h_usd": "24小时总成交量",
    "btc_dominance": "BTC 市占率",
    "eth_dominance": "ETH 市占率",
    "stablecoin_supply_usd": "稳定币供应",
    "stablecoin_dominance": "稳定币市占率",
    "altcoin_dominance": "山寨币市占率",
    "dominance_breakdown": "市占率拆分",
    "sector_rotation": "板块轮动",
    "market_cap_usd": "市值",
    "market_cap_change_24h_pct": "24小时市值变化",
    "stablecoin_assets": "主要稳定币",
    "defi_tvl_usd": "DeFi TVL",
    "capital_flow_inputs": "资金流输入",
    "contract_derivatives": "合约衍生品数据",
    "public_liquidity_proxy": "公开流动性代理数据",
    "available_fields": "可用字段",
    "funding_rate": "资金费率",
    "open_interest_contracts": "持仓量",
    "open_interest_usd": "持仓量美元价值",
    "open_interest_change_24h_pct": "持仓量24小时变化",
    "long_short_ratio": "多空比",
    "quote_volume_24h": "24小时成交额",
    "spread": "买卖价差",
    "errors": "数据错误",
    "note": "说明",
    "label": "标签",
    "value": "数值",
    "previous_close": "前值",
    "date": "日期",
    "unit": "单位",
    "symbol": "标的",
    "active_cryptocurrencies": "活跃币种数量",
    "markets": "市场数量",
}


class ReportGenerator:
    """Markdown 日报生成器"""

    def __init__(self, output_dir: str = "data/reports"):
        self._output_dir = output_dir

    @property
    def output_dir(self) -> str:
        """报告输出目录。"""
        return self._output_dir

    def generate(self, context: MarketContext) -> str:
        """
        生成完整 Markdown 日报。
        返回 Markdown 文本，同时保存文件。
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M")

        sections = []

        # 标题
        sections.append(f"# BushQ Crypto AI 日报")
        sections.append(f"> 生成时间: {date_str}")
        sections.append("")

        ai: Optional[AIAnalysis] = None
        for sym, analysis in context.analyses.items():
            if analysis.ai:
                ai = analysis.ai
                break

        if ai and _is_v31(ai):
            sections.extend(_render_v31_summary(ai, context))
            sections.append("")

        # 市场概览
        sections.append("## 市场概览")
        sections.append("")
        sections.append("| 币种 | 价格(USDT) | 24h涨跌 | 24h高 | 24h低 | 资金费率 |")
        sections.append("|------|-----------|---------|-------|-------|---------|")
        for symbol, ticker in context.tickers.items():
            coin = _display_symbol(symbol)
            fr_str = f"{ticker.funding_rate:.6f}" if ticker.funding_rate is not None else "-"
            sections.append(
                f"| {coin} | {ticker.price:.2f} | {ticker.change_24h:+.2f}% | "
                f"{ticker.high_24h:.2f} | {ticker.low_24h:.2f} | {fr_str} |"
            )
        sections.append("")

        # 情绪指数
        if context.fear_greed:
            fg = context.fear_greed
            fg_cn = FG_CLASSIFICATION_MAP.get(fg.classification, fg.classification)
            sections.append("## 市场情绪")
            sections.append("")
            sections.append(f"- **恐惧贪婪指数**: {fg.value} ({fg_cn})")
            if fg.previous_day is not None:
                sections.append(f"- 昨日: {fg.previous_day}")
            if fg.previous_week is not None:
                sections.append(f"- 上周: {fg.previous_week}")
            sections.append("")

        # 技术分析
        sections.append("## 技术分析")
        sections.append("")
        for symbol, tf_analyses in context.tech_analyses.items():
            coin = _display_symbol(symbol)
            for timeframe, tech in tf_analyses.items():
                sections.append(f"### {coin} - {timeframe}")
                sections.append(f"- 趋势: **{tech.trend}**")
                sections.append(f"- RSI: {tech.rsi:.1f} ({tech.rsi_signal})")
                sections.append(f"- MACD: {tech.macd_signal}")
                sections.append(f"- 布林带: {tech.bollinger_position}")
                if tech.support_levels:
                    sections.append(f"- 支撑位: {', '.join(str(s) for s in tech.support_levels)}")
                if tech.resistance_levels:
                    sections.append(f"- 阻力位: {', '.join(str(r) for r in tech.resistance_levels)}")
                sections.append("")

        # AI 综合分析
        if ai and _is_v31(ai):
            sections.extend(_render_v31_details(ai))
        elif ai:
            phase_cn = PHASE_MAP.get(_safe_text(ai.market_phase), _cn_value(ai.market_phase))
            sections.append("## AI 综合分析")
            sections.append("")
            sections.append(f"**市场阶段**: {phase_cn} | **信心程度**: {_cn_value(ai.confidence)} | **风险等级**: {_cn_value(ai.risk_level) or '-'}")
            if ai.phase_reason:
                sections.append(f"**阶段依据**: {_safe_text(ai.phase_reason)}")
            sections.append("")
            sections.append(
                f"**市场评分**: {ai.market_score:.0f} | "
                f"**多头评分**: {ai.bullish_score:.0f} | "
                f"**空头评分**: {ai.bearish_score:.0f} | "
                f"**趋势强度**: {ai.trend_strength:.0f}"
            )
            sections.append("")
            if ai.macro:
                sections.append("### 宏观环境")
                sections.append(f"- 风险模式: {_cn_value(ai.macro.get('risk_mode')) or '-'}")
                if ai.macro.get("summary"):
                    sections.append(f"- 总结: {_safe_text(ai.macro.get('summary'))}")
                sections.append("")
            if ai.market_structure:
                sections.append("### 市场结构")
                for key, value in ai.market_structure.items():
                    sections.append(f"- {_cn_key(key)}: {_format_value_cn(value)}")
                sections.append("")

            if ai.capital_flow:
                sections.append("### 资金流")
                sections.append(f"- 方向: {_cn_value(ai.capital_flow.get('direction')) or '-'}")
                sections.append(f"- 强度: {_cn_value(ai.capital_flow.get('strength')) or '-'}")
                if ai.capital_flow.get("summary"):
                    sections.append(f"- 总结: {_safe_text(ai.capital_flow.get('summary'))}")
                if ai.capital_flow.get("evidence"):
                    sections.append(f"- 依据: {_format_value_cn(ai.capital_flow.get('evidence'))}")
                if ai.capital_flow.get("leverage_state"):
                    sections.append(f"- 杠杆状态: {_cn_value(ai.capital_flow.get('leverage_state'))}")
                sections.append("")

            if ai.onchain_analysis:
                sections.append("### 链上分析")
                for key in ["status", "impact", "summary", "data_gap"]:
                    if ai.onchain_analysis.get(key):
                        sections.append(f"- {_cn_key(key)}: {_format_value_cn(ai.onchain_analysis.get(key))}")
                sections.append("")

            if ai.sentiment:
                sections.append("### 情绪")
                if ai.sentiment.get("fear_greed"):
                    sections.append(f"- Fear & Greed: {_safe_text(ai.sentiment.get('fear_greed'))}")
                if ai.sentiment.get("social"):
                    sections.append(f"- 社交情绪: {_safe_text(ai.sentiment.get('social'))}")
                if ai.sentiment.get("overall"):
                    sections.append(f"- 综合情绪: {_safe_text(ai.sentiment.get('overall'))}")
                sections.append("")

            if ai.news_impact:
                sections.append("### 新闻影响")
                if ai.news_impact.get("overall"):
                    sections.append(f"- 整体影响: {_safe_text(ai.news_impact.get('overall'))}")
                events = ai.news_impact.get("important_events", [])
                for event in events[:8] if isinstance(events, list) else []:
                    sections.append(f"- {_format_event(event)}")
                sections.append("")

            if ai.market_summary:
                sections.append(f"**市场总结**: {_safe_text(ai.market_summary)}")
                sections.append("")

            if ai.risk_alerts:
                sections.append("### 风险提示")
                for alert in ai.risk_alerts:
                    sections.append(f"- {_format_event(alert)}")
                sections.append("")

            if ai.key_observations:
                sections.append("### 关键观察")
                for obs in ai.key_observations:
                    sections.append(f"- {_format_event(obs)}")
                sections.append("")

            if ai.watch_items:
                sections.append("### 后续关注")
                for item in ai.watch_items:
                    sections.append(f"- {_format_event(item)}")
                sections.append("")

            if ai.symbol_analysis:
                sections.append("### 币种分析")
                for sym, detail in ai.symbol_analysis.items():
                    coin = _display_symbol(sym)
                    if isinstance(detail, dict):
                        sections.append(f"#### {coin}")
                        if detail.get("trend"):
                            sections.append(f"- 趋势: {_safe_text(detail.get('trend'))}")
                        if detail.get("strength"):
                            sections.append(f"- 强度: {_safe_text(detail.get('strength'))}")
                        if detail.get("support"):
                            sections.append(f"- 支撑: {_format_levels(detail.get('support'))}")
                        if detail.get("resistance"):
                            sections.append(f"- 压力: {_format_levels(detail.get('resistance'))}")
                        if detail.get("technical_summary"):
                            sections.append(f"- 技术: {_safe_text(detail.get('technical_summary'))}")
                        if detail.get("volume"):
                            sections.append(f"- 成交量: {_safe_text(detail.get('volume'))}")
                        if detail.get("funding_rate"):
                            sections.append(f"- 资金费率: {_safe_text(detail.get('funding_rate'))}")
                        if detail.get("open_interest"):
                            sections.append(f"- 持仓量: {_safe_text(detail.get('open_interest'))}")
                        if detail.get("risk"):
                            sections.append(f"- 风险: {_safe_text(detail.get('risk'))}")
                        if detail.get("summary"):
                            sections.append(f"- 总结: {_safe_text(detail.get('summary'))}")
                    else:
                        sections.append(f"- **{coin}**: {_safe_text(detail)}")
                sections.append("")
        else:
            ai_errors = [err for err in context.errors if "AI" in err or "DeepSeek" in err]
            if ai_errors:
                sections.append("## AI 综合分析")
                sections.append("")
                sections.append("- AI 分析本次未生成。")
                for err in ai_errors:
                    sections.append(f"- 原因: {_safe_text(err)}")
                sections.append("")

        # 新闻
        if context.news and context.news.items:
            sections.append("## 最新新闻")
            sections.append("")
            for i, item in enumerate(context.news.items[:10], 1):
                sections.append(f"{i}. [{item.source}] {item.title}")
                if item.url:
                    sections.append(f"   [链接]({item.url})")
            sections.append("")

        # 免责声明
        sections.append("---")
        sections.append("*本报告由 BushQ Crypto AI 自动生成，仅供参考，不构成投资建议。*")

        # 拼接
        markdown = "\n".join(sections)

        # 保存文件
        self._save_file(markdown, now)

        # 生成简要版
        context.report_brief = self._generate_brief(context, ai, date_str, markdown)

        return markdown

    def _generate_brief(
        self,
        context: MarketContext,
        ai: Optional[AIAnalysis],
        date_str: str,
        markdown: str = "",
    ) -> str:
        """生成简要版报告（用于推送摘要）"""
        lines = []
        lines.append(f"**BushQ Crypto AI 日报 {date_str}**")
        lines.append("")

        conclusion_lines = extract_report_summary_lines(markdown, max_lines=10)
        if conclusion_lines:
            lines.append("**今日结论**")
            lines.extend(conclusion_lines)
            lines.append("")

        # 行情一句话
        price_parts = []
        for symbol, ticker in context.tickers.items():
            coin = _display_symbol(symbol)
            price_parts.append(f"{coin} {ticker.price:.2f}({ticker.change_24h:+.2f}%)")
        lines.append(" ".join(price_parts))

        # 情绪
        if context.fear_greed:
            fg_cn = FG_CLASSIFICATION_MAP.get(context.fear_greed.classification, context.fear_greed.classification)
            lines.append(f"情绪指数: {context.fear_greed.value}({fg_cn})")

        # AI 总结
        if ai and not conclusion_lines:
            if _is_v31(ai):
                phase = _safe_dict(ai.raw.get("market_phase"))
                scores = _safe_dict(ai.raw.get("scores"))
                guidance = _safe_dict(_safe_dict(ai.raw.get("position_guidance")).get("overall"))
                lines.append(
                    f"市场状态: {_cn_value(phase.get('label') or 'Unknown')} "
                    f"({ _cn_value(phase.get('confidence') or 'low') }) | "
                    f"风险: {_cn_value(scores.get('risk_level') or 'Medium')}"
                )
                lines.append(
                    f"仓位参考: {_cn_value(guidance.get('label') or 'Watch Only')} / "
                    f"{_safe_text(guidance.get('suggested_band')) or '0%'}"
                )
                if guidance.get("entry_condition"):
                    lines.append(f"条件: {_safe_text(guidance.get('entry_condition'))}")
                if guidance.get("invalidation"):
                    lines.append(f"失效: {_safe_text(guidance.get('invalidation'))}")
                if phase.get("reason"):
                    lines.append(f"核心依据: {_safe_text(phase.get('reason'))}")
            else:
                phase_cn = PHASE_MAP.get(_safe_text(ai.market_phase), _cn_value(ai.market_phase))
                summary = _safe_text(ai.market_summary) or _safe_text(ai.macro.get("summary") if ai.macro else "")
                lines.append(f"市场阶段: {phase_cn} | {summary}")
            if ai.risk_alerts:
                lines.append("风险: " + "; ".join(_format_event(x) for x in ai.risk_alerts[:3]))

        lines.append("")
        lines.append("*仅供参考，不构成投资建议*")
        return "\n".join(lines)

    def _save_file(self, content: str, now: datetime) -> None:
        """保存报告到文件"""
        os.makedirs(self._output_dir, exist_ok=True)
        filename = f"report_{now.strftime('%Y%m%d_%H%M')}.md"
        filepath = os.path.join(self._output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("报告已保存: %s", filepath)


def _display_symbol(symbol: str) -> str:
    """将交易对或合约 ID 转为报告中的币种简称。"""
    if symbol.endswith("-USDT-SWAP"):
        return symbol.replace("-USDT-SWAP", "")
    return symbol.replace("/USDT", "")


def extract_report_summary_lines(content: str, max_lines: int = 12) -> list:
    """Extract the concise conclusion block from a generated Markdown report."""
    summary_lines = []
    capture = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in {"## 今日结论", "## AI 综合分析"}:
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if not capture or not stripped:
            continue
        if stripped.startswith("### "):
            break
        summary_lines.append(stripped)
        if len(summary_lines) >= max_lines:
            break
    return summary_lines


def _is_v31(ai: AIAnalysis) -> bool:
    return _safe_text(ai.metadata.get("version")) == "3.1" or "position_guidance" in ai.raw or "symbols" in ai.raw


def _render_v31_summary(ai: AIAnalysis, context: Optional[MarketContext] = None) -> list:
    raw = ai.raw
    phase = _safe_dict(raw.get("market_phase"))
    scores = _safe_dict(raw.get("scores"))
    guidance = _safe_dict(_safe_dict(raw.get("position_guidance")).get("overall"))
    sections = ["## 今日结论", ""]
    sections.append(f"- 市场状态: {_cn_value(phase.get('label') or 'Unknown')}（置信度: {_cn_value(phase.get('confidence') or 'low')}）")
    sections.append(f"- 风险等级: {_cn_value(scores.get('risk_level') or 'Medium')}")
    sections.append(
        f"- 仓位参考: {_cn_value(guidance.get('label') or 'Watch Only')} / "
        f"{_safe_text(guidance.get('suggested_band')) or '0%'}"
    )
    entry_condition = _safe_text(guidance.get("entry_condition"))
    invalidation = _safe_text(guidance.get("invalidation"))
    if _is_insufficient_text(entry_condition) and context:
        entry_condition = _fallback_entry_condition(context)
    if _is_insufficient_text(invalidation) and context:
        invalidation = _fallback_invalidation(context)
    sections.append(f"- 入场条件: {entry_condition or '当前数据不足以支持该结论。'}")
    sections.append(f"- 失效条件: {invalidation or '当前数据不足以支持该结论。'}")
    sections.append("- 操作解读: 仅作市场研究参考，不构成投资建议。")
    sections.append(f"- 核心依据: {_safe_text(phase.get('reason')) or '当前数据不足以支持该结论。'}")

    symbols = [item for item in _safe_list(raw.get("symbols")) if isinstance(item, dict) and _safe_text(item.get("symbol"))]
    if symbols:
        sections.extend(["", "## 关键价位", ""])
        for item in symbols:
            symbol = _safe_text(item.get("symbol"))
            scenario = _safe_dict(item.get("scenario"))
            support = item.get("support", [])
            resistance = item.get("resistance", [])
            entry_zone = _safe_dict(item.get("entry_zone"))
            if context:
                fallback_support, fallback_resistance = _fallback_levels(symbol, context)
                if not _format_levels(support):
                    support = fallback_support
                if not _format_levels(resistance):
                    resistance = fallback_resistance
                if not entry_zone:
                    entry_zone = _fallback_entry_zone(symbol, context)
            sections.append(
                f"- {symbol or '-'}: 压力 {_format_levels(resistance) or '-'}；"
                f"支撑 {_format_levels(support) or '-'}；"
                f"观察入场 {_format_entry_zone(entry_zone) or '-'}；"
                f"突破场景 {_safe_text(scenario.get('if_breakout')) or '-'}；"
                f"跌破场景 {_safe_text(scenario.get('if_breakdown')) or '-'}"
            )

    risks = _safe_list(raw.get("risk_alerts"))
    if risks:
        sections.extend(["", "## 风险提示", ""])
        for risk in risks[:5]:
            sections.append(f"- {_format_event(risk)}")
    return sections


def _render_v31_details(ai: AIAnalysis) -> list:
    raw = ai.raw
    scores = _safe_dict(raw.get("scores"))
    sections = ["## 详细分析", ""]
    sections.append(
        f"**市场评分**: {_safe_text(scores.get('market_score')) or '0'} | "
        f"**多头评分**: {_safe_text(scores.get('bullish_score')) or '0'} | "
        f"**空头评分**: {_safe_text(scores.get('bearish_score')) or '0'} | "
        f"**趋势强度**: {_safe_text(scores.get('trend_strength')) or '0'}"
    )
    if scores.get("score_evidence"):
        sections.append(f"**评分依据**: {_safe_text(scores.get('score_evidence'))}")
    sections.append("")

    for title, key in [
        ("宏观环境", "macro"),
        ("市场结构", "market_structure"),
        ("资金流", "capital_flow"),
        ("链上分析", "onchain"),
        ("情绪", "sentiment"),
    ]:
        value = _safe_dict(raw.get(key))
        if value:
            sections.append(f"### {title}")
            for item_key, item_value in value.items():
                formatted = _format_value_cn(item_value)
                if formatted:
                    sections.append(f"- {_cn_key(item_key)}: {formatted}")
            sections.append("")

    news = _safe_list(raw.get("news_impact"))
    if news:
        sections.append("### 新闻影响")
        for item in news[:8]:
            sections.append(f"- {_format_event(item)}")
        sections.append("")

    observations = _safe_list(raw.get("key_observations"))
    if observations:
        sections.append("### 关键观察")
        for item in observations[:8]:
            sections.append(f"- {_format_event(item)}")
        sections.append("")

    follow_up = _safe_list(raw.get("follow_up"))
    if follow_up:
        sections.append("### 后续关注")
        for item in follow_up[:8]:
            sections.append(f"- {_format_event(item)}")
        sections.append("")

    symbols = [item for item in _safe_list(raw.get("symbols")) if isinstance(item, dict) and _safe_text(item.get("symbol"))]
    if symbols:
        sections.append("### 币种分析")
        for item in symbols:
            sections.append(f"#### {_safe_text(item.get('symbol'))}")
            for key in ["state", "technical_summary", "risk"]:
                if item.get(key):
                    sections.append(f"- {_cn_key(key)}: {_format_value_cn(item.get(key))}")
            if item.get("support"):
                sections.append(f"- 支撑: {_format_levels(item.get('support'))}")
            if item.get("resistance"):
                sections.append(f"- 压力: {_format_levels(item.get('resistance'))}")
            entry_zone = _safe_dict(item.get("entry_zone"))
            if entry_zone:
                sections.append(f"- 观察入场区域: {_format_entry_zone(entry_zone)}")
            scenario = _safe_dict(item.get("scenario"))
            if scenario:
                sections.append(f"- 突破场景: {_safe_text(scenario.get('if_breakout'))}")
                sections.append(f"- 跌破场景: {_safe_text(scenario.get('if_breakdown'))}")
            if item.get("evidence"):
                sections.append(f"- 依据: {_safe_text(item.get('evidence'))}")
        sections.append("")

    validation = _safe_dict(raw.get("validation"))
    if validation and (validation.get("warnings") or validation.get("unsupported_claims_removed")):
        sections.append("### 校验提示")
        if validation.get("warnings"):
            sections.append(f"- 提示: {_format_value_cn(validation.get('warnings'))}")
        if validation.get("unsupported_claims_removed"):
            sections.append(f"- 已移除无依据结论: {_format_value_cn(validation.get('unsupported_claims_removed'))}")
        sections.append("")
    return sections


def _safe_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _is_insufficient_text(value: str) -> bool:
    text = _safe_text(value)
    return not text or "当前数据不足" in text or text in {"Unknown", "unknown", "-"}


def _fallback_levels(symbol: str, context: MarketContext) -> tuple[list, list]:
    supports = []
    resistances = []
    tf_map = context.tech_analyses.get(symbol, {}) if context else {}
    for timeframe in ["1d", "4h"]:
        tech = tf_map.get(timeframe)
        if not tech:
            continue
        if not supports and tech.support_levels:
            supports = tech.support_levels
        if not resistances and tech.resistance_levels:
            resistances = tech.resistance_levels
    ticker = context.tickers.get(symbol) if context else None
    if ticker:
        if not supports and ticker.low_24h:
            supports = [round(ticker.low_24h, 6)]
        if not resistances and ticker.high_24h:
            resistances = [round(ticker.high_24h, 6)]
    return supports, resistances


def _fallback_entry_zone(symbol: str, context: MarketContext) -> dict:
    support, resistance = _fallback_levels(symbol, context)
    zone = {
        "near_support": support[:2] if isinstance(support, list) else [],
        "breakout_above": resistance[0] if isinstance(resistance, list) and resistance else "",
        "invalid_below": support[0] if isinstance(support, list) and support else "",
        "condition": "仅在价格接近支撑后企稳，或放量突破压力后观察；不构成买入建议。",
        "evidence": [],
    }
    if support:
        zone["evidence"].append(f"技术支撑: {_format_levels(support)}")
    if resistance:
        zone["evidence"].append(f"技术压力: {_format_levels(resistance)}")
    return zone


def _fallback_entry_condition(context: MarketContext) -> str:
    samples = []
    for symbol in list(context.tickers.keys())[:3]:
        support, resistance = _fallback_levels(symbol, context)
        coin = _display_symbol(symbol)
        if support and resistance:
            samples.append(f"{coin} 接近支撑 { _format_levels(support) } 后企稳，或放量突破压力 { _format_levels(resistance) }")
    if samples:
        return "；".join(samples) + "。仅作观察条件，不构成操作建议。"
    return "等待价格重新站上关键压力，且成交量、Funding/OI 未同步恶化后再观察。"


def _fallback_invalidation(context: MarketContext) -> str:
    samples = []
    for symbol in list(context.tickers.keys())[:3]:
        support, _resistance = _fallback_levels(symbol, context)
        coin = _display_symbol(symbol)
        if support:
            samples.append(f"{coin} 跌破支撑 { _format_levels(support) }")
    if samples:
        return "；".join(samples) + "，且资金费率/OI 转弱时，反弹观察假设失效。"
    return "跌破关键支撑且资金费率/OI 转弱时，当前反弹观察假设失效。"


def _cn_key(key: Any) -> str:
    text = _safe_text(key)
    return KEY_CN_MAP.get(text, text)


def _cn_value(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    normalized = text.strip().lower()
    mapped = VALUE_CN_MAP.get(normalized) or VALUE_CN_MAP.get(normalized.replace("_", " "))
    return mapped if mapped else text


def _format_value_cn(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item in (None, "", []):
                continue
            parts.append(f"{_cn_key(key)}: {_format_value_cn(item)}")
        return "；".join(parts)
    if isinstance(value, list):
        if not value:
            return ""
        if all(not isinstance(item, (dict, list)) for item in value):
            return "、".join(_cn_value(item) for item in value if _cn_value(item))
        return "；".join(_format_value_cn(item) for item in value if _format_value_cn(item))
    return _cn_value(value)


def _format_event(value) -> str:
    if isinstance(value, dict):
        parts = []
        labels = {
            "level": _cn_key("level"),
            "type": _cn_key("type"),
            "topic": _cn_key("topic"),
            "title": _cn_key("title"),
            "event": _cn_key("event"),
            "impact": _cn_key("impact"),
            "direction": _cn_key("direction"),
            "duration": _cn_key("duration"),
            "summary": _cn_key("summary"),
            "reason": _cn_key("reason"),
            "evidence": _cn_key("evidence"),
            "data_to_watch": _cn_key("data_to_watch"),
            "watch_data": _cn_key("watch_data"),
            "source": _cn_key("source"),
            "url": _cn_key("url"),
            "published_at": _cn_key("published_at"),
            "confidence": "置信度",
        }
        for key, label in labels.items():
            if value.get(key):
                parts.append(f"{label}: {_format_value_cn(value.get(key))}")
        return " | ".join(parts) if parts else _format_value_cn(value)
    return _format_value_cn(value)


def _format_entry_zone(value) -> str:
    zone = _safe_dict(value)
    if not zone:
        return ""
    parts = []
    near_support = _format_levels(zone.get("near_support"))
    breakout_above = _safe_text(zone.get("breakout_above"))
    invalid_below = _safe_text(zone.get("invalid_below"))
    condition = _safe_text(zone.get("condition"))
    if near_support:
        parts.append(f"支撑附近 {near_support}")
    if breakout_above:
        parts.append(f"突破 {breakout_above} 后确认")
    if invalid_below:
        parts.append(f"跌破 {invalid_below} 失效")
    if condition:
        parts.append(condition)
    return "；".join(parts)


def _format_levels(value) -> str:
    if isinstance(value, list):
        return ", ".join(_safe_text(v) for v in value)
    return _safe_text(value)
