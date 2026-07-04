"""宏观、市场结构和公开链上数据采集器"""

import logging
import csv
import io
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from fetchers.base import BaseFetcher
from models.macro import MacroData, MarketStructureData, OnchainPublicData

logger = logging.getLogger("cic.fetcher.macro_market")


class MacroMarketFetcher(BaseFetcher):
    """采集免费宏观和市场结构数据。"""

    def __init__(self):
        super().__init__("MacroMarket")
        self._timeout = 15
        self._proxies: Optional[Dict[str, str]] = None

    def initialize(self, config: Any) -> None:
        self._timeout = config.get("macro.timeout", 15)
        proxy = config.get("macro.proxy", "") or config.get("exchange.proxy", "")
        self._proxies = {"http": proxy, "https": proxy} if proxy else None
        self._initialized = True
        logger.info("[MacroMarket] 初始化成功 (proxy=%s)", "有" if proxy else "无")

    def health_check(self) -> bool:
        try:
            data = self.fetch_market_structure()
            return bool(data and data.btc_dominance)
        except Exception as e:
            logger.warning("[MacroMarket] 健康检查失败: %s", e)
            return False

    def fetch(self, **kwargs) -> Dict[str, Any]:
        return self.fetch_all()

    def fetch_all(self) -> Dict[str, Any]:
        macro = self.fetch_macro()
        market_structure = self.fetch_market_structure()
        onchain_public = self.fetch_onchain_public()
        self._enrich_market_structure(market_structure, onchain_public)
        return {
            "macro": macro,
            "market_structure": market_structure,
            "onchain_public": onchain_public,
        }

    def fetch_macro(self) -> MacroData:
        errors = []
        dxy_errors = []
        dxy = self._fetch_yahoo_quote(["DX-Y.NYB", "DX=F"], "DXY", dxy_errors)
        if dxy.get("value") is None:
            dxy = self._fetch_fred_series("DTWEXBGS", "Broad Dollar Index proxy", errors)
        if dxy.get("value") is None:
            errors.extend(dxy_errors)
        yields = {
            "2y": self._fetch_fred_series("DGS2", "US Treasury 2Y", errors),
            "5y": self._fetch_fred_series("DGS5", "US Treasury 5Y", errors),
            "10y": self._fetch_fred_series("DGS10", "US Treasury 10Y", errors),
            "30y": self._fetch_fred_series("DGS30", "US Treasury 30Y", errors),
        }
        for value in yields.values():
            if isinstance(value.get("value"), (int, float)) and value["value"] > 20:
                value["value"] = value["value"] / 10
                value["unit"] = "%"

        summary_parts = []
        if dxy.get("value"):
            summary_parts.append(f"DXY {dxy['value']:.2f}")
        if yields.get("10y", {}).get("value"):
            summary_parts.append(f"美债10Y {yields['10y']['value']:.2f}%")
        return MacroData(
            dxy=dxy,
            treasury_yields=yields,
            summary="; ".join(summary_parts) if summary_parts else "当前数据不足以支持该结论。",
            errors=errors,
            source="yahoo_finance",
        )

    def fetch_market_structure(self) -> MarketStructureData:
        errors = []
        try:
            data = self._get_json("https://api.coingecko.com/api/v3/global").get("data", {})
            market_cap_pct = data.get("market_cap_percentage", {}) or {}
            total_market_cap = data.get("total_market_cap", {}) or {}
            total_volume = data.get("total_volume", {}) or {}
            result = MarketStructureData(
                total_market_cap_usd=float(total_market_cap.get("usd") or 0),
                total_volume_24h_usd=float(total_volume.get("usd") or 0),
                btc_dominance=float(market_cap_pct.get("btc") or 0),
                eth_dominance=float(market_cap_pct.get("eth") or 0),
                dominance_breakdown={
                    str(key): float(value)
                    for key, value in market_cap_pct.items()
                    if isinstance(value, (int, float)) or _is_float(value)
                },
                active_cryptocurrencies=int(data.get("active_cryptocurrencies") or 0),
                markets=int(data.get("markets") or 0),
                source="coingecko_global",
            )
            result.summary = (
                f"总市值 ${result.total_market_cap_usd:,.0f}; "
                f"BTC Dominance {result.btc_dominance:.2f}%; "
                f"ETH Dominance {result.eth_dominance:.2f}%"
            )
            return result
        except Exception as e:
            errors.append(str(e))
            logger.warning("[MacroMarket] CoinGecko global 失败: %s", e)

        try:
            data = self._get_json("https://api.coinlore.net/api/global/")
            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                raise ValueError("CoinLore global 返回格式异常")
            result = MarketStructureData(
                total_market_cap_usd=float(data.get("total_mcap") or 0),
                total_volume_24h_usd=float(data.get("total_volume") or 0),
                btc_dominance=float(data.get("btc_d") or 0),
                eth_dominance=float(data.get("eth_d") or 0),
                dominance_breakdown={
                    "btc": float(data.get("btc_d") or 0),
                    "eth": float(data.get("eth_d") or 0),
                },
                active_cryptocurrencies=int(data.get("coins_count") or 0),
                markets=int(data.get("active_markets") or 0),
                source="coinlore_global",
                errors=errors,
            )
            result.summary = (
                f"总市值 ${result.total_market_cap_usd:,.0f}; "
                f"BTC Dominance {result.btc_dominance:.2f}%; "
                f"ETH Dominance {result.eth_dominance:.2f}%"
            )
            logger.info("[MacroMarket] 使用 CoinLore global 备用市场结构数据")
            return result
        except Exception as fallback_error:
            errors.append(f"coinlore_global: {fallback_error}")
            logger.warning("[MacroMarket] CoinLore global 失败: %s", fallback_error)
            return MarketStructureData(summary="当前数据不足以支持该结论。", errors=errors, source="coingecko_global")

    def fetch_onchain_public(self) -> OnchainPublicData:
        errors = []
        stablecoin_supply = 0.0
        stable_assets = []
        defi_tvl = 0.0

        try:
            stable_data = self._get_json("https://stablecoins.llama.fi/stablecoins", params={"includePrices": "true"})
            for asset in stable_data.get("peggedAssets", []) or []:
                supply = _extract_stablecoin_usd(asset)
                if supply <= 0:
                    continue
                stablecoin_supply += supply
                stable_assets.append({
                    "symbol": asset.get("symbol") or asset.get("name", ""),
                    "name": asset.get("name", ""),
                    "supply_usd": supply,
                })
            stable_assets.sort(key=lambda x: x["supply_usd"], reverse=True)
            stable_assets = stable_assets[:8]
        except Exception as e:
            errors.append(f"stablecoins: {e}")
            logger.warning("[MacroMarket] DefiLlama stablecoins 失败: %s", e)

        try:
            charts = self._get_json("https://api.llama.fi/charts")
            if isinstance(charts, list) and charts:
                latest = charts[-1]
                defi_tvl = float(latest.get("totalLiquidityUSD") or 0)
        except Exception as e:
            errors.append(f"defi_tvl: {e}")
            logger.warning("[MacroMarket] DefiLlama TVL 失败: %s", e)

        summary_parts = []
        if stablecoin_supply:
            summary_parts.append(f"稳定币供应 ${stablecoin_supply:,.0f}")
        if defi_tvl:
            summary_parts.append(f"DeFi TVL ${defi_tvl:,.0f}")
        return OnchainPublicData(
            stablecoin_supply_usd=stablecoin_supply,
            stablecoin_assets=stable_assets,
            defi_tvl_usd=defi_tvl,
            summary="; ".join(summary_parts) if summary_parts else "当前数据不足以支持该结论。",
            errors=errors,
            source="defillama",
        )

    def _enrich_market_structure(self, market_structure: MarketStructureData, onchain_public: OnchainPublicData) -> None:
        if market_structure.total_market_cap_usd and onchain_public.stablecoin_supply_usd:
            market_structure.stablecoin_dominance = (
                onchain_public.stablecoin_supply_usd / market_structure.total_market_cap_usd * 100
            )
        known = market_structure.btc_dominance + market_structure.eth_dominance + market_structure.stablecoin_dominance
        market_structure.altcoin_dominance = max(0.0, 100.0 - known)
        breakdown = dict(market_structure.dominance_breakdown or {})
        if market_structure.btc_dominance:
            breakdown["btc"] = market_structure.btc_dominance
        if market_structure.eth_dominance:
            breakdown["eth"] = market_structure.eth_dominance
        if market_structure.stablecoin_dominance:
            breakdown["stablecoins"] = market_structure.stablecoin_dominance
        breakdown["others_ex_btc_eth_stablecoins"] = market_structure.altcoin_dominance
        market_structure.dominance_breakdown = breakdown

        try:
            categories = self._get_json("https://api.coingecko.com/api/v3/coins/categories")
            if isinstance(categories, list):
                usable = []
                for item in categories:
                    if not isinstance(item, dict):
                        continue
                    market_cap = float(item.get("market_cap") or 0)
                    change = item.get("market_cap_change_24h")
                    if market_cap < 100_000_000 or change is None:
                        continue
                    usable.append({
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "market_cap_usd": market_cap,
                        "market_cap_change_24h_pct": float(change),
                    })
                usable.sort(key=lambda x: abs(x["market_cap_change_24h_pct"]), reverse=True)
                market_structure.sector_rotation = usable[:8]
        except Exception as e:
            market_structure.errors.append(f"sector_rotation: {e}")
            logger.warning("[MacroMarket] CoinGecko categories 失败: %s", e)

    def validate(self, data: Any) -> bool:
        return isinstance(data, (MacroData, MarketStructureData, OnchainPublicData, dict))

    def normalize(self, raw_data: Any) -> Any:
        return raw_data

    def _fetch_yahoo_quote(self, symbols: list[str], label: str, errors: list[str]) -> Dict[str, Any]:
        for symbol in symbols:
            try:
                encoded = quote(symbol, safe="")
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
                data = self._get_json(url, params={"range": "5d", "interval": "1d"})
                result = data.get("chart", {}).get("result", []) or []
                if not result:
                    continue
                meta = result[0].get("meta", {})
                value = meta.get("regularMarketPrice") or meta.get("previousClose")
                previous = meta.get("chartPreviousClose")
                return {
                    "symbol": symbol,
                    "label": label,
                    "value": float(value) if value is not None else None,
                    "previous_close": float(previous) if previous is not None else None,
                    "currency": meta.get("currency", ""),
                    "unit": "%",
                    "source": "yahoo_finance",
                }
            except Exception as e:
                errors.append(f"{label}/{symbol}: {e}")
        return {"label": label, "value": None, "source": "yahoo_finance"}

    def _fetch_fred_series(self, series_id: str, label: str, errors: list[str]) -> Dict[str, Any]:
        try:
            resp = requests.get(
                "https://fred.stlouisfed.org/graph/fredgraph.csv",
                params={"id": series_id},
                timeout=self._timeout,
                proxies=self._proxies,
            )
            resp.raise_for_status()
            rows = list(csv.DictReader(io.StringIO(resp.text)))
            previous_value = None
            for row in reversed(rows):
                raw_value = row.get(series_id)
                if raw_value and raw_value != ".":
                    value = float(raw_value)
                    return {
                        "symbol": series_id,
                        "label": label,
                        "value": value,
                        "previous_close": previous_value,
                        "date": row.get("observation_date", ""),
                        "unit": "%" if series_id.startswith("DGS") else "index",
                        "source": "fred",
                    }
                if raw_value and raw_value != ".":
                    previous_value = float(raw_value)
        except Exception as e:
            errors.append(f"{label}/{series_id}: {e}")
        return {"symbol": series_id, "label": label, "value": None, "source": "fred"}

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = requests.get(url, params=params, timeout=self._timeout, proxies=self._proxies)
        resp.raise_for_status()
        return resp.json()


def _extract_stablecoin_usd(asset: Dict[str, Any]) -> float:
    for key in ["circulating", "circulatingPrevDay", "circulatingPrevWeek"]:
        value = asset.get(key)
        if isinstance(value, dict) and value.get("peggedUSD") is not None:
            return float(value.get("peggedUSD") or 0)
    if asset.get("pegMechanism") and asset.get("price") and asset.get("supply"):
        return float(asset.get("price") or 0) * float(asset.get("supply") or 0)
    return 0.0


def _is_float(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
