"""腾讯财经数据适配器 —— 以腾讯财经 API 为主要数据源"""

import re
from typing import Optional
import pandas as pd
import httpx

from app.utils.logger import logger

_TENCENT_BASE = "https://web.ifzq.gtimg.cn"
_QT_BASE = "https://qt.gtimg.cn"
_SH_SZ_CACHE: dict[str, str] = {}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "KHTML, like Gecko Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://gu.qq.com/",
}


async def _get_exchange(code: str) -> str:
    """判断股票所属交易所: 6开头→sh, 其余→sz"""
    if code in _SH_SZ_CACHE:
        return _SH_SZ_CACHE[code]
    # 尝试 sh 前缀
    exchange = "sh" if code.startswith("6") else "sz"
    _SH_SZ_CACHE[code] = exchange
    return exchange


async def fetch_stock_kline(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """腾讯财经股票日线K线 (JSON)"""
    try:
        exchange = await _get_exchange(code)
        url = (
            f"{_TENCENT_BASE}/appstock/app/fqkline/get"
            f"?param={exchange}{code},day,{start},{end},2000,qfq"
        )
        async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0 or not data.get("data"):
            logger.warning(f"[tencent] 股票 {code} K线无数据")
            return None

        key = f"{exchange}{code}"
        raw_list = data["data"].get(key, {}).get("qfqday", [])
        if not raw_list:
            # 尝试 day 字段
            raw_list = data["data"].get(key, {}).get("day", [])

        if not raw_list:
            logger.warning(f"[tencent] 股票 {code} K线记录为空")
            return None

        rows = []
        for item in raw_list:
            if len(item) >= 6:
                rows.append({
                    "date": item[0],
                    "open": float(item[1]),
                    "close": float(item[2]),
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": float(item[5]) if item[5] else 0,
                })
        df = pd.DataFrame(rows)
        df["code"] = code
        # 补全 pct_chg
        if len(df) > 1:
            df["pct_chg"] = df["close"].pct_change() * 100
        else:
            df["pct_chg"] = 0.0
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        logger.info(f"[tencent] 获取股票K线成功 {code}, {len(df)} 条")
        return df
    except Exception as e:
        logger.error(f"[tencent] 获取股票K线失败 {code}: {e}")
        return None


async def fetch_stock_realtime(code: str) -> Optional[dict]:
    """腾讯财经股票实时行情"""
    try:
        exchange = await _get_exchange(code)
        url = f"{_QT_BASE}/q={exchange}{code}"
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10) as client:
            resp = await client.get(url)
            resp.encoding = "gbk"
            text = resp.text

        match = re.search(r'"(.*?)"', text)
        if not match:
            return None
        fields = match.group(1).split("~")
        if len(fields) < 38:
            return None

        return {
            "name": fields[1],
            "code": fields[2],
            "price": float(fields[3]) if fields[3] else 0,
            "yesterday_close": float(fields[4]) if fields[4] else 0,
            "open": float(fields[5]) if fields[5] else 0,
            "high": float(fields[33]) if fields[33] else 0,
            "low": float(fields[34]) if fields[34] else 0,
            "volume": float(fields[36]) if fields[36] else 0,
            "amount": float(fields[37]) if fields[37] else 0,
            "change": float(fields[31]) if fields[31] else 0,
            "change_pct": float(fields[32]) if fields[32] else 0,
        }
    except Exception as e:
        logger.error(f"[tencent] 获取实时行情失败 {code}: {e}")
        return None


async def fetch_fund_kline(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """腾讯财经基金历史净值
    注意: 腾讯K线接口不支持基金，此函数仅作占位
         实际基金历史净值需回退到 akshare
    """
    return None


async def fetch_fund_nav_realtime(code: str) -> Optional[dict]:
    """腾讯财经基金实时净值

    返回格式: code~name~?~?~~unit_nav~acc_nav~change_pct~date~
    字段索引: 0=code, 1=name, 5=unit_nav, 6=acc_nav, 7=change_pct, 8=date
    """
    try:
        url = f"{_QT_BASE}/q=jj{code}"
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10) as client:
            resp = await client.get(url)
            resp.encoding = "gbk"
            text = resp.text

        match = re.search(r'"(.*?)"', text)
        if not match:
            return None
        fields = match.group(1).split("~")
        if len(fields) < 9:
            return None

        nav_str = fields[5].strip()
        acc_nav_str = fields[6].strip()
        pct_str = fields[7].strip()

        return {
            "name": fields[1],
            "code": fields[0],
            "nav": float(nav_str) if nav_str else 0,
            "acc_nav": float(acc_nav_str) if acc_nav_str else 0,
            "change_pct": float(pct_str) if pct_str else 0,
            "date": fields[8] if fields[8] else "",
        }
    except Exception as e:
        logger.error(f"[tencent] 获取基金实时净值失败 {code}: {e}")
        return None


async def fetch_fund_holdings(code: str) -> Optional[dict]:
    """腾讯财经基金持仓信息（季报持仓）"""
    try:
        url = (
            f"{_TENCENT_BASE}/fund/newfund/fundInvesting/getInvesting"
            f"?app=web&symbol=jj{code}"
        )
        async with httpx.AsyncClient(headers=_HEADERS, timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            return None

        raw = data.get("data", {})
        return {
            "asset_allocation": raw.get("peizhi", []),
            "industry_allocation": raw.get("hangye", []),
            "top_stocks": raw.get("zhongcang", []),
        }
    except Exception as e:
        logger.error(f"[tencent] 获取基金持仓失败 {code}: {e}")
        return None
