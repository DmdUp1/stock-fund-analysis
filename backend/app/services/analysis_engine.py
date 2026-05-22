"""分析引擎：股票技术指标 + 基金净值分析"""

import numpy as np
import pandas as pd
from scipy import stats

from app.utils.logger import logger


# ═══════════════════════════════════════════════════════════
# 通用计算
# ═══════════════════════════════════════════════════════════

def calculate_price_percentile(df: pd.DataFrame, period: int = 252) -> float:
    """计算当前价格在 period 天内的分位值（0~1）"""
    if df is None or df.empty or len(df) < 2:
        return 0.5
    closes = df["close"].values[-period:]
    if len(closes) < 2:
        return 0.5
    current = closes[-1]
    percentile = stats.percentileofscore(closes, current) / 100.0
    return round(float(percentile), 4)


def calculate_ma(df: pd.DataFrame, period: int) -> float:
    if df is None or df.empty or len(df) < period:
        return 0.0
    return float(df["close"].rolling(period).mean().iloc[-1])


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    if df is None or df.empty or len(df) < period + 1:
        return 50.0
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0


def calculate_macd(df: pd.DataFrame) -> dict:
    if df is None or df.empty or len(df) < 26:
        return {"dif": 0.0, "dea": 0.0, "hist": 0.0}
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    hist = 2 * (dif - dea)
    return {
        "dif": round(float(dif.iloc[-1]), 4),
        "dea": round(float(dea.iloc[-1]), 4),
        "hist": round(float(hist.iloc[-1]), 4),
    }


def calculate_bollinger(df: pd.DataFrame, period: int = 20) -> dict:
    if df is None or df.empty or len(df) < period:
        return {"mid": 0.0, "upper": 0.0, "lower": 0.0}
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    return {
        "mid": round(float(mid.iloc[-1]), 2),
        "upper": round(float((mid + 2 * std).iloc[-1]), 2),
        "lower": round(float((mid - 2 * std).iloc[-1]), 2),
    }


def calculate_volatility(df: pd.DataFrame, period: int = 60) -> float:
    if df is None or df.empty or len(df) < period:
        return 0.0
    returns = df["close"].pct_change().dropna()
    return float(returns.tail(period).std() * np.sqrt(252))


# ═══════════════════════════════════════════════════════════
# 股票技术分析
# ═══════════════════════════════════════════════════════════

def analyze_stock_technicals(df: pd.DataFrame) -> dict:
    """全量股票技术分析"""
    try:
        return {
            "ma5": calculate_ma(df, 5),
            "ma10": calculate_ma(df, 10),
            "ma20": calculate_ma(df, 20),
            "ma60": calculate_ma(df, 60),
            "rsi": calculate_rsi(df, 14),
            "macd": calculate_macd(df),
            "bollinger": calculate_bollinger(df),
            "volatility": calculate_volatility(df),
            "price_percentile_252d": calculate_price_percentile(df, 252),
            "price_percentile_60d": calculate_price_percentile(df, 60),
            "high_52w": float(df["high"].tail(252).max()) if len(df) > 0 else 0.0,
            "low_52w": float(df["low"].tail(252).min()) if len(df) > 0 else 0.0,
            "close": float(df["close"].iloc[-1]) if len(df) > 0 else 0.0,
            "change_pct": float(df["pct_chg"].iloc[-1]) if "pct_chg" in df.columns and len(df) > 0 else 0.0,
        }
    except Exception as e:
        logger.error(f"[analysis_engine] 股票技术分析失败: {e}")
        return {}


# ═══════════════════════════════════════════════════════════
# 基金分析
# ═══════════════════════════════════════════════════════════

def analyze_fund_metrics(df: pd.DataFrame) -> dict:
    """基金净值分析（基于净值数据）"""
    try:
        result = {
            "nav": float(df["close"].iloc[-1]) if len(df) > 0 else 0.0,
            "acc_nav": float(df["acc_nav"].iloc[-1]) if "acc_nav" in df.columns and len(df) > 0 else 0.0,
            "nav_percentile_1y": calculate_price_percentile(df, min(252, len(df))),
            "nav_percentile_3m": calculate_price_percentile(df, min(60, len(df))),
            "volatility": calculate_volatility(df),
            "max_nav_1y": float(df["close"].tail(252).max()) if len(df) > 0 else 0.0,
            "min_nav_1y": float(df["close"].tail(252).min()) if len(df) > 0 else 0.0,
            "change_pct": float(df["pct_chg"].iloc[-1]) if "pct_chg" in df.columns and len(df) > 0 else 0.0,
        }

        # 计算累计收益率
        if "acc_nav" in df.columns and len(df) > 0:
            first_acc = float(df["acc_nav"].iloc[0])
            last_acc = float(df["acc_nav"].iloc[-1])
            result["total_return"] = round((last_acc - first_acc) / first_acc * 100, 2) if first_acc > 0 else 0.0

        # 计算最大回撤
        if len(df) > 1:
            peak = df["close"].cummax()
            drawdown = (df["close"] - peak) / peak
            result["max_drawdown"] = round(float(drawdown.min()) * 100, 2)

        return result
    except Exception as e:
        logger.error(f"[analysis_engine] 基金分析失败: {e}")
        return {}
