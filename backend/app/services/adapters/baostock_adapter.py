"""baostock 数据适配器 —— 获取 A 股行情（备用数据源）"""

from typing import Optional
import pandas as pd

from app.utils.logger import logger


async def fetch_market_data(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """通过 baostock 获取日线行情（备用数据源）"""
    try:
        import baostock as bs

        bs.login()
        # baostock code 格式: sh.600000 / sz.000001
        prefix = "sh" if code.startswith("6") else "sz"
        bs_code = f"{prefix}.{code}"

        rs = bs.query_history_k_data_plus(
            bs_code,
            fields="date,open,close,high,low,volume,amount",
            start_date=start.replace("-", ""),
            end_date=end.replace("-", ""),
            frequency="d",
            adjustflag="2",  # 前复权
        )
        bs.logout()

        if rs.error_code != "0":
            logger.warning(f"[baostock] 查询失败 {code}: {rs.error_msg}")
            return None

        rows = []
        while rs.next():
            rows.append(rs.get_row_data())

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume", "amount"])
        for col in ["open", "close", "high", "low", "volume", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["code"] = code
        return df
    except Exception as e:
        logger.error(f"[baostock] 获取行情失败 {code}: {e}")
        return None
