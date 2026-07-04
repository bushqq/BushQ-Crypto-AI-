"""技术指标分析模块"""

import logging
from typing import Dict, List, Optional

import pandas as pd
import ta

from models.kline import KlineData
from models.analysis import TechnicalAnalysis

logger = logging.getLogger("cic.analyzer.technical")


class TechnicalAnalyzer:
    """基于 K 线数据计算技术指标"""

    def analyze(self, symbol: str, timeframe: str, klines: List[KlineData]) -> Optional[TechnicalAnalysis]:
        """
        对单个币种单个周期进行技术分析。
        输入 K 线列表（从旧到新），输出 TechnicalAnalysis。
        """
        if len(klines) < 10:
            logger.warning("[TechAnalysis] %s %s K线不足10根，跳过", symbol, timeframe)
            return None

        try:
            df = self._klines_to_df(klines)

            # MA
            df["ma_7"] = ta.trend.sma_indicator(df["close"], window=7)
            df["ma_25"] = ta.trend.sma_indicator(df["close"], window=25)
            df["ma_99"] = ta.trend.sma_indicator(df["close"], window=99)

            # RSI
            df["rsi"] = ta.momentum.rsi(df["close"], window=14)

            # MACD
            macd = ta.trend.MACD(df["close"])
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            df["macd_hist"] = macd.macd_diff()

            # 布林带
            bollinger = ta.volatility.BollingerBands(df["close"])
            df["bb_upper"] = bollinger.bollinger_hband()
            df["bb_middle"] = bollinger.bollinger_mavg()
            df["bb_lower"] = bollinger.bollinger_lband()

            # 取最后一行
            last = df.iloc[-1]
            close = last["close"]

            # ---- 信号判断 ----
            ma_signals = {}
            if pd.notna(last["ma_7"]) and pd.notna(last["ma_25"]):
                ma_signals["MA7>MA25"] = "多" if last["ma_7"] > last["ma_25"] else "空"
            if pd.notna(last["ma_7"]):
                ma_signals["价格vs_MA7"] = "多" if close > last["ma_7"] else "空"

            # RSI 信号
            rsi_val = last["rsi"] if pd.notna(last["rsi"]) else 50.0
            if rsi_val > 70:
                rsi_signal = "超买"
            elif rsi_val < 30:
                rsi_signal = "超卖"
            elif rsi_val > 55:
                rsi_signal = "偏多"
            elif rsi_val < 45:
                rsi_signal = "偏空"
            else:
                rsi_signal = "中性"

            # MACD 信号
            macd_val = last.get("macd", 0)
            macd_sig_val = last.get("macd_signal", 0)
            macd_hist_val = last.get("macd_hist", 0)
            if pd.notna(macd_hist_val):
                macd_signal = "多" if macd_hist_val > 0 else "空"
            else:
                macd_signal = "中性"

            # 布林带位置
            bb_pos = "中性"
            if pd.notna(last["bb_upper"]) and pd.notna(last["bb_lower"]):
                if close > last["bb_upper"]:
                    bb_pos = "上轨上方（超买区）"
                elif close < last["bb_lower"]:
                    bb_pos = "下轨下方（超卖区）"
                elif close > last["bb_middle"]:
                    bb_pos = "中轨上方（偏多）"
                else:
                    bb_pos = "中轨下方（偏空）"

            # 趋势判断
            trend = self._determine_trend(df)

            # 支撑/阻力位（简易版：优先近30根；数据不足时使用现有K线）
            recent = df.tail(min(30, len(df)))
            support = float(recent["low"].min())
            resistance = float(recent["high"].max())

            # 综合摘要
            summary = self._build_summary(symbol, timeframe, close, rsi_val, rsi_signal, macd_signal, bb_pos, trend)

            result = TechnicalAnalysis(
                symbol=symbol,
                timeframe=timeframe,
                ma_signals=ma_signals,
                rsi=round(rsi_val, 2),
                rsi_signal=rsi_signal,
                macd_signal=macd_signal,
                bollinger_position=bb_pos,
                trend=trend,
                support_levels=[round(support, 2)],
                resistance_levels=[round(resistance, 2)],
                summary=summary,
            )

            logger.info("[TechAnalysis] %s %s: RSI=%.1f(%s) MACD=%s 趋势=%s",
                        symbol, timeframe, rsi_val, rsi_signal, macd_signal, trend)
            return result

        except Exception as e:
            logger.error("[TechAnalysis] 分析失败 %s %s: %s", symbol, timeframe, e)
            return None

    def analyze_all(self, klines_data: Dict[str, Dict[str, List[KlineData]]]) -> Dict[str, Dict[str, TechnicalAnalysis]]:
        """批量分析所有币种所有周期"""
        results = {}
        for symbol, tf_klines in klines_data.items():
            results[symbol] = {}
            for timeframe, klines in tf_klines.items():
                analysis = self.analyze(symbol, timeframe, klines)
                if analysis:
                    results[symbol][timeframe] = analysis
        return results

    def _klines_to_df(self, klines: List[KlineData]) -> pd.DataFrame:
        """KlineData 列表转 DataFrame"""
        data = [{
            "timestamp": k.timestamp,
            "open": k.open,
            "high": k.high,
            "low": k.low,
            "close": k.close,
            "volume": k.volume,
        } for k in klines]
        df = pd.DataFrame(data)
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        return df

    def _determine_trend(self, df: pd.DataFrame) -> str:
        """判断趋势方向"""
        if len(df) < 25:
            return "数据不足"
        last_close = df.iloc[-1]["close"]
        ma7 = df.iloc[-1].get("ma_7")
        ma25 = df.iloc[-1].get("ma_25")

        if pd.isna(ma25):
            return "数据不足"

        if last_close > ma7 > ma25:
            return "上升趋势"
        elif last_close < ma7 < ma25:
            return "下降趋势"
        else:
            return "震荡"

    def _build_summary(self, symbol, timeframe, close, rsi, rsi_signal, macd_signal, bb_pos, trend) -> str:
        """构建简短摘要"""
        return (
            f"{symbol} {timeframe}: 价格{close:.2f}, "
            f"趋势{trend}, RSI {rsi:.1f}({rsi_signal}), "
            f"MACD {macd_signal}, 布林{bb_pos}"
        )
