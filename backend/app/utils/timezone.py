"""北京时间 (UTC+8) 工具模块"""

import datetime

# 北京时间时区对象
BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Shanghai")


def beijing_now() -> datetime.datetime:
    """返回当前北京时间 (naive datetime，隐含时区为 UTC+8)"""
    return datetime.datetime.now(BEIJING_TZ).replace(tzinfo=None)


def beijing_today() -> datetime.date:
    """返回今天的北京时间日期"""
    return datetime.datetime.now(BEIJING_TZ).date()


def beijing_from_timestamp(ts: float) -> datetime.datetime:
    """将 Unix 时间戳转换为北京时间 (naive datetime)"""
    return datetime.datetime.fromtimestamp(ts, tz=BEIJING_TZ).replace(tzinfo=None)
