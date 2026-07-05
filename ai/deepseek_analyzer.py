"""DeepSeek AI 分析模块"""

import json
import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI

from models.analysis import AIAnalysis
from models.market_context import MarketContext

logger = logging.getLogger("cic.ai")


# 系统 Prompt - 当外部模板不可用时使用的安全兜底版本。
SYSTEM_PROMPT = """You are Crypto Market Intelligence Analyst V3.1.
Analyze only the supplied input JSON. Do not predict prices, recommend trades, or fabricate facts.
If evidence is missing, output "当前数据不足以支持该结论。"
Return one valid JSON object only. Do not output Markdown, comments, prose, or code fences.
Every conclusion, score, risk alert, and symbol summary must include evidence.
Use the V3.1 JSON contract: metadata, data_quality, market_phase, scores, macro, market_structure, capital_flow, onchain, sentiment, news_impact, risk_alerts, key_observations, follow_up, position_guidance, symbols, validation."""


class DeepSeekAnalyzer:
    """DeepSeek AI 分析器"""

    def __init__(self):
        self._client: Optional[OpenAI] = None
        self._model: str = "deepseek-v4-pro"
        self._max_tokens: int = 4096
        self._temperature: float = 0.3
        self._timeout: int = 120
        self._system_prompt: str = SYSTEM_PROMPT

    def initialize(self, config: Any) -> None:
        """初始化 DeepSeek 客户端"""
        api_key = config.get("ai.api_key", "")
        base_url = config.get("ai.base_url", "https://api.deepseek.com")
        self._model = config.get("ai.model", "deepseek-v4-pro")
        self._max_tokens = config.get("ai.max_tokens", 4096)
        self._temperature = config.get("ai.temperature", 0.3)
        self._timeout = config.get("ai.timeout", 120)
        self._system_prompt = self._load_prompt_template(config.get("ai.prompt_template", ""))

        if not api_key:
            logger.warning("[DeepSeek] API Key 未配置，AI 分析不可用")
            return

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=self._timeout,
        )
        logger.info("[DeepSeek] 初始化成功 (model=%s)", self._model)

    def analyze(self, context: MarketContext) -> Optional[AIAnalysis]:
        """
        执行 AI 综合分析。
        将市场数据整理为文本，发送给 DeepSeek，解析返回结果。
        """
        if not self._client:
            logger.error("[DeepSeek] 客户端未初始化")
            return None

        attempts = [
            {
                "name": "primary",
                "system": self._system_prompt,
                "user": self._build_user_message(context, news_limit=12),
                "json_mode": True,
            },
            {
                "name": "retry_compact",
                "system": SYSTEM_PROMPT,
                "user": self._build_user_message(context, news_limit=8),
                "json_mode": False,
            },
            {
                "name": "retry_minimal",
                "system": SYSTEM_PROMPT,
                "user": self._build_user_message(context, news_limit=3, compact=True),
                "json_mode": True,
            },
        ]

        for attempt in attempts:
            try:
                logger.info("[DeepSeek] 开始 AI 分析 (%s)...", attempt["name"])
                raw_content = self._request_completion(
                    system_prompt=attempt["system"],
                    user_message=attempt["user"],
                    json_mode=attempt["json_mode"],
                )
                try:
                    parsed = _parse_json_object(raw_content)
                except (json.JSONDecodeError, ValueError) as parse_error:
                    logger.warning("[DeepSeek] JSON 解析失败 (%s): %s", attempt["name"], parse_error)
                    repaired_content = self._repair_json_response(raw_content, parse_error)
                    parsed = _parse_json_object(repaired_content)
                ai_result = _to_ai_analysis(parsed)
                _apply_context_facts(ai_result, context)
                logger.info("[DeepSeek] 分析完成: phase=%s confidence=%s", ai_result.market_phase, ai_result.confidence)
                return ai_result
            except json.JSONDecodeError as e:
                logger.warning("[DeepSeek] JSON 修复后仍解析失败 (%s): %s", attempt["name"], e)
            except ValueError as e:
                logger.warning("[DeepSeek] JSON 修复后仍无效 (%s): %s", attempt["name"], e)
            except Exception as e:
                logger.error("[DeepSeek] 分析失败 (%s): %s", attempt["name"], e)

        logger.error("[DeepSeek] 两次尝试后仍未获得可解析 JSON")
        return None

    def _request_completion(self, system_prompt: str, user_message: str, json_mode: bool) -> str:
        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        raw_content = choice.message.content or ""
        if not raw_content:
            logger.warning(
                "[DeepSeek] 返回为空: finish_reason=%s prompt_tokens=%s completion_tokens=%s",
                getattr(choice, "finish_reason", None),
                getattr(getattr(response, "usage", None), "prompt_tokens", None),
                getattr(getattr(response, "usage", None), "completion_tokens", None),
            )
        preview = raw_content[:300].replace("\n", " ")
        logger.debug("[DeepSeek] 原始返回预览: %s", preview if preview else "<empty>")
        return raw_content

    def _repair_json_response(self, raw_content: str, parse_error: Exception) -> str:
        """Ask the model to repair malformed JSON without changing the analysis."""
        content = (raw_content or "").strip()
        if not content:
            raise ValueError("AI 返回为空，无法修复")

        logger.info("[DeepSeek] 尝试自动修复 JSON，原始字节: %d", len(content.encode("utf-8")))
        repair_prompt = (
            "Fix the following malformed JSON and return one valid JSON object only.\n"
            "Do not add Markdown, code fences, comments, explanations, or new analysis.\n"
            "Preserve the original meaning and fields. Only repair JSON syntax.\n"
            f"Parser error: {parse_error}\n\n"
            f"{content}"
        )
        return self._request_completion(
            system_prompt="You repair malformed JSON. Return valid JSON only.",
            user_message=repair_prompt,
            json_mode=True,
        )

    def _build_user_message(self, context: MarketContext, news_limit: int = 20, compact: bool = False) -> str:
        """将 MarketContext 转换为 V3.1 输入 JSON。"""
        payload = {
            "metadata": {
                "run_id": context.run_id,
                "run_time": context.run_time,
                "timezone": "Asia/Shanghai",
                "symbols": list(context.tickers.keys()),
                "intervals": sorted({tf for tf_map in context.tech_analyses.values() for tf in tf_map.keys()}),
            },
            "market": [
                {
                    "symbol": symbol,
                    "price": ticker.price,
                    "change_24h": ticker.change_24h,
                    "high_24h": ticker.high_24h,
                    "low_24h": ticker.low_24h,
                    "volume_24h": ticker.volume_24h,
                    "quote_volume": ticker.quote_volume,
                    "funding_rate": ticker.funding_rate,
                    "open_interest": ticker.open_interest,
                    "open_interest_usd": ticker.open_interest_usd,
                    "open_interest_change_24h": ticker.open_interest_change_24h,
                    "long_short_ratio": ticker.long_short_ratio,
                    "bid_price": ticker.bid_price,
                    "ask_price": ticker.ask_price,
                    "spread": ticker.spread,
                    "timestamp": ticker.timestamp,
                    "exchange": ticker.exchange,
                }
                for symbol, ticker in context.tickers.items()
            ],
            "technical": [
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "rsi": tech.rsi,
                    "rsi_signal": tech.rsi_signal,
                    "macd_signal": tech.macd_signal,
                    "bollinger_position": tech.bollinger_position,
                    "trend": tech.trend,
                    "support": tech.support_levels,
                    "resistance": tech.resistance_levels,
                    "summary": tech.summary,
                }
                for symbol, tf_analyses in context.tech_analyses.items()
                for timeframe, tech in tf_analyses.items()
            ],
            "sentiment": {
                "fear_greed": None if not context.fear_greed else {
                    "value": context.fear_greed.value,
                    "classification": context.fear_greed.classification,
                    "previous_day": context.fear_greed.previous_day,
                    "previous_week": context.fear_greed.previous_week,
                    "timestamp": context.fear_greed.timestamp,
                },
                "social": "当前数据不足以支持该结论。",
            },
            "news": [
                {
                    "title": item.title,
                    "source": item.source or "unknown",
                    "url": item.url,
                    "published_at": item.published_at,
                    "raw_summary": "" if compact else item.summary,
                    "sentiment": item.sentiment,
                    "relevance_score": 1 if item.title and item.url else 0,
                }
                for item in ((context.news.items[:news_limit]) if context.news else [])
            ],
            "coin_info": [] if compact else [
                {
                    "symbol": symbol,
                    "name": info.name,
                    "market_cap_rank": info.market_cap_rank,
                    "market_cap": info.market_cap,
                    "circulating_supply": info.circulating_supply,
                    "total_supply": info.total_supply,
                    "sector": info.sector,
                }
                for symbol, info in context.coin_infos.items()
            ],
            "macro": _macro_payload(context),
            "market_structure": _market_structure_payload(context),
            "capital_flow_inputs": _capital_flow_inputs(context),
            "onchain": _onchain_payload(context),
            "required_behavior": {
                "missing_data_text": "当前数据不足以支持该结论。",
                "output_language": "Chinese",
                "no_markdown": True,
                "json_contract": "Crypto Market Intelligence V3.1",
                "compact_output": compact,
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _load_prompt_template(self, template_path: str) -> str:
        """加载用户可编辑 Prompt 模板。"""
        if not template_path:
            return SYSTEM_PROMPT
        path = template_path
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
            if prompt:
                logger.info("[DeepSeek] 已加载 Prompt 模板: %s", path)
                return prompt
        except Exception as e:
            logger.warning("[DeepSeek] Prompt 模板加载失败，使用默认模板: %s", e)
        return SYSTEM_PROMPT


def _display_symbol(symbol: str) -> str:
    """将交易对或合约 ID 转为报告中的币种简称。"""
    if symbol.endswith("-USDT-SWAP"):
        return symbol.replace("-USDT-SWAP", "")
    return symbol.replace("/USDT", "")


def _macro_payload(context: MarketContext) -> Dict:
    if not context.macro:
        return {
            "status": "missing",
            "note": "当前数据不足以支持该结论。",
            "dxy": None,
            "treasury_yields": {},
        }
    return {
        "status": "available" if context.macro.dxy or context.macro.treasury_yields else "insufficient",
        "summary": context.macro.summary,
        "dxy": context.macro.dxy,
        "treasury_yields": context.macro.treasury_yields,
        "source": context.macro.source,
        "errors": context.macro.errors,
    }


def _market_structure_payload(context: MarketContext) -> Dict:
    if not context.market_structure:
        return {"status": "missing", "summary": "当前数据不足以支持该结论。"}
    ms = context.market_structure
    return {
        "status": "available" if ms.btc_dominance or ms.total_market_cap_usd else "insufficient",
        "summary": ms.summary,
        "total_market_cap_usd": ms.total_market_cap_usd,
        "total_volume_24h_usd": ms.total_volume_24h_usd,
        "btc_dominance": ms.btc_dominance,
        "eth_dominance": ms.eth_dominance,
        "stablecoin_dominance": ms.stablecoin_dominance,
        "altcoin_dominance": ms.altcoin_dominance,
        "dominance_breakdown": ms.dominance_breakdown,
        "sector_rotation": ms.sector_rotation,
        "active_cryptocurrencies": ms.active_cryptocurrencies,
        "markets": ms.markets,
        "source": ms.source,
        "errors": ms.errors,
    }


def _capital_flow_inputs(context: MarketContext) -> Dict:
    contract_items = []
    for symbol, ticker in context.tickers.items():
        contract_items.append({
            "symbol": symbol,
            "funding_rate": ticker.funding_rate,
            "open_interest_contracts": ticker.open_interest,
            "open_interest_usd": ticker.open_interest_usd,
            "open_interest_change_24h_pct": ticker.open_interest_change_24h,
            "long_short_ratio": ticker.long_short_ratio,
            "quote_volume_24h": ticker.quote_volume,
            "spread": ticker.spread,
            "exchange": ticker.exchange,
        })

    public_onchain = _onchain_payload(context)
    available_fields = []
    for item in contract_items:
        if item.get("funding_rate") is not None:
            available_fields.append("funding_rate")
        if item.get("open_interest_contracts") is not None:
            available_fields.append("open_interest")
        if item.get("open_interest_change_24h_pct") is not None:
            available_fields.append("open_interest_change_24h")
        if item.get("long_short_ratio") is not None:
            available_fields.append("long_short_ratio")
        if item.get("quote_volume_24h"):
            available_fields.append("quote_volume_24h")
    if public_onchain.get("stablecoin_supply_usd"):
        available_fields.append("stablecoin_supply_usd")
    if public_onchain.get("defi_tvl_usd"):
        available_fields.append("defi_tvl_usd")

    return {
        "status": "available" if available_fields else "insufficient",
        "contract_derivatives": contract_items,
        "public_liquidity_proxy": public_onchain,
        "available_fields": sorted(set(available_fields)),
        "data_gaps": [
            "exchange_netflow",
            "etf_flow",
            "large_wallet_position_change",
            "liquidation",
        ],
        "note": "资金流方向只能基于 Funding、OI、多空比、成交额和稳定币/DeFi 公开代理数据谨慎判断；缺少交易所净流入和 ETF 资金流时不得输出强结论。",
    }


def _onchain_payload(context: MarketContext) -> Dict:
    if not context.onchain_public:
        return {"status": "missing", "summary": "当前数据不足以支持该结论。"}
    oc = context.onchain_public
    return {
        "status": oc.status,
        "summary": oc.summary,
        "stablecoin_supply_usd": oc.stablecoin_supply_usd,
        "stablecoin_assets": oc.stablecoin_assets,
        "defi_tvl_usd": oc.defi_tvl_usd,
        "source": oc.source,
        "errors": oc.errors,
        "note": "这是免费公开稳定币和 DeFi TVL 代理数据，不等同于 Glassnode/CryptoQuant 级别链上深度数据。",
    }


def _safe_dict(value) -> Dict:
    return value if isinstance(value, dict) else {}


def _parse_json_object(raw_content: str) -> Dict:
    content = (raw_content or "").strip()
    if not content:
        raise ValueError("AI 返回为空")

    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            preview = content[:200].replace("\n", " ")
            raise ValueError(f"AI 返回不是 JSON，预览: {preview}")
        parsed = json.loads(content[start:end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("AI 返回 JSON 不是对象")
    return parsed


def _to_ai_analysis(parsed: Dict) -> AIAnalysis:
    market_phase_raw = parsed.get("market_phase", "")
    market_phase = _safe_dict(market_phase_raw) if isinstance(market_phase_raw, dict) else {}
    scores = _safe_dict(parsed.get("scores"))
    macro = _safe_dict(parsed.get("macro"))
    news_impact = parsed.get("news_impact", {})
    symbols = parsed.get("symbols", {})
    symbol_map = _symbols_to_map(symbols)
    onchain = _safe_dict(parsed.get("onchain")) or _safe_dict(parsed.get("onchain_analysis"))
    follow_up = parsed.get("follow_up", parsed.get("watch_items"))
    return AIAnalysis(
        timestamp=_safe_scalar(parsed.get("timestamp", "")) or _safe_scalar(_safe_dict(parsed.get("metadata")).get("generated_at", "")),
        metadata=_safe_dict(parsed.get("metadata")),
        data_quality=_safe_list(parsed.get("data_quality")),
        macro=macro,
        market_structure=_safe_dict(parsed.get("market_structure")),
        market_summary=_safe_scalar(parsed.get("market_summary", "")) or _safe_scalar(macro.get("summary", "")) or _safe_scalar(market_phase.get("reason", "")),
        risk_alerts=_safe_list(parsed.get("risk_alerts")),
        market_phase=_safe_scalar(market_phase.get("label", parsed.get("market_phase", ""))),
        phase_reason=_safe_scalar(parsed.get("phase_reason", "")) or _safe_scalar(market_phase.get("reason", "")),
        trend_strength=_safe_number(parsed.get("trend_strength", scores.get("trend_strength", 0))),
        market_score=_safe_number(parsed.get("market_score", scores.get("market_score", 0))),
        bullish_score=_safe_number(parsed.get("bullish_score", scores.get("bullish_score", 0))),
        bearish_score=_safe_number(parsed.get("bearish_score", scores.get("bearish_score", 0))),
        key_observations=_safe_list(parsed.get("key_observations")),
        watch_items=_safe_list(follow_up),
        news_impact=news_impact if isinstance(news_impact, (dict, list)) else {},
        capital_flow=_safe_dict(parsed.get("capital_flow")),
        onchain_analysis=onchain,
        sentiment=_safe_dict(parsed.get("sentiment")),
        position_guidance=_safe_dict(parsed.get("position_guidance")),
        symbol_analysis=symbol_map or _safe_dict(parsed.get("symbol_analysis")),
        confidence=_safe_scalar(parsed.get("confidence", market_phase.get("confidence", "low"))),
        risk_level=_safe_scalar(parsed.get("risk_level", scores.get("risk_level", ""))),
        validation=_safe_dict(parsed.get("validation")),
        raw=parsed,
    )


def _apply_context_facts(ai_result: AIAnalysis, context: MarketContext) -> None:
    """Use collected facts to correct obvious AI contradictions before reporting."""
    raw = ai_result.raw

    macro_payload = _macro_payload(context)
    macro_has_data = bool(
        _safe_dict(macro_payload.get("dxy")).get("value")
        or any(_safe_dict(item).get("value") for item in _safe_dict(macro_payload.get("treasury_yields")).values())
    )
    if macro_has_data:
        macro = _safe_dict(raw.get("macro"))
        summary = _safe_scalar(macro.get("summary"))
        if not macro or "DXY" not in summary or "美债" not in summary:
            dxy_value = _safe_dict(macro_payload.get("dxy")).get("value")
            y10 = _safe_dict(_safe_dict(macro_payload.get("treasury_yields")).get("10y")).get("value")
            evidence = []
            if dxy_value is not None:
                evidence.append(f"DXY代理数据: {dxy_value}")
            if y10 is not None:
                evidence.append(f"美债10Y收益率: {y10}%")
            macro = {
                "risk_mode": macro.get("risk_mode") or "Unknown",
                "summary": macro_payload.get("summary") or "宏观数据已采集，但方向仍需结合风险资产表现确认。",
                "evidence": evidence or ["宏观数据已采集"],
            }
            raw["macro"] = macro
            ai_result.macro = macro

    market_structure_payload = _market_structure_payload(context)
    if market_structure_payload.get("status") == "available":
        ms = _safe_dict(raw.get("market_structure"))
        bad_gaps = {
            "total_market_cap",
            "total_market_cap_usd",
            "btc_dominance",
            "total_volume",
            "total_volume_24h_usd",
            "stablecoin_dominance",
            "altcoin_dominance_detail",
            "sector_rotation",
        }
        gaps = [str(item) for item in _safe_list(ms.get("data_gaps"))]
        if not ms or _safe_scalar(ms.get("status")).lower() == "missing" or any(gap in bad_gaps for gap in gaps):
            evidence = []
            if market_structure_payload.get("total_market_cap_usd"):
                evidence.append(f"加密总市值: ${market_structure_payload['total_market_cap_usd']:,.0f}")
            if market_structure_payload.get("total_volume_24h_usd"):
                evidence.append(f"24h总成交量: ${market_structure_payload['total_volume_24h_usd']:,.0f}")
            if market_structure_payload.get("btc_dominance"):
                evidence.append(f"BTC市占率: {market_structure_payload['btc_dominance']:.2f}%")
            if market_structure_payload.get("eth_dominance"):
                evidence.append(f"ETH市占率: {market_structure_payload['eth_dominance']:.2f}%")
            if market_structure_payload.get("stablecoin_dominance"):
                evidence.append(f"稳定币市占率: {market_structure_payload['stablecoin_dominance']:.2f}%")
            if market_structure_payload.get("altcoin_dominance"):
                evidence.append(f"其他山寨币市占率: {market_structure_payload['altcoin_dominance']:.2f}%")
            ms = {
                "summary": market_structure_payload.get("summary") or "市场结构数据已采集。",
                "status": "available",
                "evidence": evidence[:4],
                "data_gaps": [],
            }
            raw["market_structure"] = ms
            ai_result.market_structure = ms

    onchain_payload = _onchain_payload(context)
    onchain_has_public_data = bool(onchain_payload.get("stablecoin_supply_usd") or onchain_payload.get("defi_tvl_usd"))
    if onchain_has_public_data:
        onchain = _safe_dict(raw.get("onchain")) or _safe_dict(raw.get("onchain_analysis"))
        gaps = [str(item) for item in _safe_list(onchain.get("data_gaps"))]
        if not onchain or _safe_scalar(onchain.get("status")).lower() == "missing" or "stablecoin_supply" in gaps:
            data_gaps = [
                "exchange_netflow",
                "whale_wallet_change",
                "active_addresses",
                "miner_balance",
                "MVRV/SOPR/NUPL",
            ]
            summary_parts = []
            if onchain_payload.get("stablecoin_supply_usd"):
                summary_parts.append(f"稳定币供应 ${onchain_payload['stablecoin_supply_usd']:,.0f}")
            if onchain_payload.get("defi_tvl_usd"):
                summary_parts.append(f"DeFi TVL ${onchain_payload['defi_tvl_usd']:,.0f}")
            onchain = {
                "status": "public_proxy",
                "impact": onchain.get("impact") or "Neutral",
                "summary": "；".join(summary_parts) + "。缺少深度链上地址数据，不能输出强链上结论。",
                "data_gaps": data_gaps,
            }
            raw["onchain"] = onchain
            ai_result.onchain_analysis = onchain

    capital_inputs = _capital_flow_inputs(context)
    public_proxy = _safe_dict(capital_inputs.get("public_liquidity_proxy"))
    if capital_inputs.get("status") == "available" and public_proxy.get("stablecoin_supply_usd"):
        capital = _safe_dict(raw.get("capital_flow"))
        summary = _safe_scalar(capital.get("summary"))
        if "稳定币供应" not in summary:
            evidence = []
            for item in _safe_list(capital_inputs.get("contract_derivatives"))[:5]:
                if not isinstance(item, dict):
                    continue
                symbol = item.get("symbol", "")
                fr = item.get("funding_rate")
                oi_change = item.get("open_interest_change_24h_pct")
                ls = item.get("long_short_ratio")
                parts = []
                if fr is not None:
                    parts.append(f"Funding {fr}")
                if oi_change is not None:
                    parts.append(f"OI 24h {oi_change:.2f}%")
                if ls is not None:
                    parts.append(f"多空比 {ls:.2f}")
                if parts:
                    evidence.append(f"{symbol}: " + ", ".join(parts))
            evidence.append(f"稳定币供应: ${public_proxy['stablecoin_supply_usd']:,.0f}")
            capital = {
                "direction": capital.get("direction") or "当前数据不足以支持强结论",
                "strength": capital.get("strength") or "弱",
                "summary": "已提供 Funding、OI、多空比、成交额和稳定币供应代理数据；缺少交易所净流入和 ETF flow，资金方向只能谨慎判断。",
                "leverage_state": capital.get("leverage_state") or "当前数据不足以支持强结论",
                "evidence": evidence[:5],
            }
            raw["capital_flow"] = capital
            ai_result.capital_flow = capital


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _symbols_to_map(value) -> Dict:
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return {}
    mapped = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        if symbol:
            mapped[str(symbol)] = item
    return mapped


def _safe_scalar(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def _safe_number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
