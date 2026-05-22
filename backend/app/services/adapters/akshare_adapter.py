"""akshare 数据适配器 —— 股票和基金的数据获取"""

from typing import Optional
import pandas as pd

from app.utils.logger import logger


# ═══════════════════════════════════════════════════════════
# 股票数据
# ═══════════════════════════════════════════════════════════

async def fetch_stock_market_data(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """A 股日线行情"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if df is None or df.empty:
            logger.warning(f"[akshare] 股票 {code} 无行情数据")
            return None

        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount", "振幅": "amplitude",
            "涨跌幅": "pct_chg", "涨跌额": "change", "换手率": "turnover",
        })
        df["code"] = code
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        logger.error(f"[akshare] 获取股票行情失败 {code}: {e}")
        return None


async def fetch_stock_fundamentals(code: str) -> Optional[dict]:
    """股票基本面摘要"""
    try:
        import akshare as ak

        financial = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
        if financial is None or financial.empty:
            return None

        latest = financial.iloc[0].to_dict()
        return {
            "pe": latest.get("市盈率-动态", None),
            "pb": latest.get("市净率", None),
            "roe": latest.get("ROE-加权", None),
            "profit_yoy": latest.get("净利润同比增长率", None),
            "revenue_yoy": latest.get("营业收入同比增长率", None),
        }
    except Exception as e:
        logger.error(f"[akshare] 获取基本面失败 {code}: {e}")
        return None


async def fetch_stock_news(code: str) -> list[dict]:
    """股票近期新闻"""
    try:
        import akshare as ak

        news = ak.stock_info_ths_news(symbol=code)
        if news is None or news.empty:
            return []
        return news.head(10).to_dict("records")
    except Exception as e:
        logger.error(f"[akshare] 获取新闻失败 {code}: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# 基金数据
# ═══════════════════════════════════════════════════════════

async def fetch_fund_nav(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """基金净值走势（开放式基金）"""
    try:
        import akshare as ak

        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            logger.warning(f"[akshare] 基金 {code} 无净值数据")
            return None

        df = df.rename(columns={
            "净值日期": "date", "单位净值": "close",
            "累计净值": "acc_nav", "日增长率": "pct_chg",
        })
        # 过滤日期区间
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df[(df["date"] >= start) & (df["date"] <= end)]
        df["code"] = code
        # 补全 open/high/low/volume 字段兼容性（基金用净值近似）
        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]
        df["volume"] = 0
        return df.reset_index(drop=True)
    except Exception as e:
        logger.error(f"[akshare] 获取基金净值失败 {code}: {e}")
        return None


async def fetch_etf_market_data(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """ETF 日线行情（场内交易的ETF）"""
    try:
        import akshare as ak

        df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if df is None or df.empty:
            logger.warning(f"[akshare] ETF {code} 无行情数据")
            return None

        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount", "涨跌幅": "pct_chg",
        })
        df["code"] = code
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        logger.error(f"[akshare] 获取ETF行情失败 {code}: {e}")
        return None


async def fetch_fund_info(code: str) -> Optional[dict]:
    """基金基本信息"""
    try:
        import akshare as ak

        info = ak.fund_open_fund_info_em(symbol=code, indicator="基金概况")
        if info is None or info.empty:
            return None

        row = info.set_index("item")["value"].to_dict() if "item" in info.columns else info.iloc[0].to_dict()
        return {
            "fund_name": row.get("基金简称", row.get("item", "")),
            "fund_type": row.get("基金类型", ""),
            "manager": row.get("基金经理", ""),
            "establish_date": row.get("成立日期", ""),
            "company": row.get("基金管理人", ""),
            "scale": row.get("资产规模", ""),
        }
    except Exception as e:
        logger.error(f"[akshare] 获取基金信息失败 {code}: {e}")
        return None


async def fetch_fund_news(code: str) -> list[dict]:
    """基金相关新闻"""
    try:
        news_data = []
        # akshare 没有专门基金新闻接口，尝试用基金代码搜索
        return news_data
    except Exception as e:
        logger.error(f"[akshare] 获取基金新闻失败 {code}: {e}")
        return []
