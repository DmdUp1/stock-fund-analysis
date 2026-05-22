"""三级缓存数据中枢：内存 → 文件 → 数据源"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Callable, Awaitable

import pandas as pd
from cachetools import TTLCache

from app.utils.config import settings
from app.utils.logger import logger

_mem_cache: TTLCache = TTLCache(maxsize=settings.MEM_CACHE_MAXSIZE, ttl=settings.MEM_CACHE_TTL)


def _cache_key(prefix: str, asset_type: str, code: str, start: str = "", end: str = "") -> str:
    raw = f"{prefix}:{asset_type}:{code}:{start}:{end}"
    return hashlib.md5(raw.encode()).hexdigest()


def _file_cache_path(key: str) -> Path:
    return settings.FILE_CACHE_DIR / f"{key}.pkl"


async def _load_from_file(key: str) -> Optional[pd.DataFrame]:
    path = _file_cache_path(key)
    if not path.exists():
        return None
    try:
        import time
        mtime = path.stat().st_mtime
        if time.time() - mtime > settings.FILE_CACHE_TTL:
            path.unlink(missing_ok=True)
            return None
        with open(path, "rb") as f:
            df = pickle.load(f)
        logger.info(f"[data_hub] 文件缓存命中: {path.name}")
        return df
    except Exception as e:
        logger.warning(f"[data_hub] 读取文件缓存失败: {e}")
        return None


async def _save_to_file(key: str, df: pd.DataFrame):
    settings.FILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _file_cache_path(key)
    try:
        with open(path, "wb") as f:
            pickle.dump(df, f)
        logger.info(f"[data_hub] 写入文件缓存: {path.name}")
    except Exception as e:
        logger.warning(f"[data_hub] 写入文件缓存失败: {e}")


async def get_market_data(
    code: str, start: str, end: str,
    fetcher: Callable[[str, str, str], Awaitable[Optional[pd.DataFrame]]],
    asset_type: str = "stock",
) -> Optional[pd.DataFrame]:
    """三级缓存获取行情/净值数据"""
    key = _cache_key("market", asset_type, code, start, end)

    if key in _mem_cache:
        logger.info(f"[data_hub] 内存缓存命中 [{asset_type}]: {code}")
        return _mem_cache[key]

    df = await _load_from_file(key)
    if df is not None:
        _mem_cache[key] = df
        return df

    logger.info(f"[data_hub] 从数据源获取 [{asset_type}]: {code}")
    df = await fetcher(code, start, end)
    if df is not None:
        _mem_cache[key] = df
        await _save_to_file(key, df)
    return df


async def get_fundamentals(
    code: str,
    fetcher: Callable[[str], Awaitable[Optional[dict]]],
    asset_type: str = "stock",
) -> Optional[dict]:
    """三级缓存获取基本面/基金信息"""
    key = _cache_key("fund", asset_type, code)

    if key in _mem_cache:
        logger.info(f"[data_hub] 内存缓存命中(基本面) [{asset_type}]: {code}")
        return _mem_cache[key]

    path = settings.FILE_CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _mem_cache[key] = data
            logger.info(f"[data_hub] 文件缓存命中(基本面) [{asset_type}]: {code}")
            return data
        except Exception:
            pass

    data = await fetcher(code)
    if data:
        _mem_cache[key] = data
        settings.FILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return data


def invalidate_cache(code: str = ""):
    global _mem_cache
    if code:
        keys = [k for k in _mem_cache if code in k]
        for k in keys:
            del _mem_cache[k]
        logger.info(f"[data_hub] 已清除 {code} 的内存缓存")
    else:
        _mem_cache.clear()
        logger.info("[data_hub] 已清除全部内存缓存")
