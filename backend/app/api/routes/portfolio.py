"""持仓管理接口 —— 股票/基金分开管理"""

import datetime

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import verify_api_key
from app.models.schemas import PortfolioSummary, PortfolioItem, Portfolio
from app.services.portfolio_manager import get_portfolio_summary, add_position, remove_position
from app.services.data_hub import get_market_data
from app.services.adapters import tencent_adapter, akshare_adapter
from app.db.database import async_session_factory
from app.db import crud
from app.utils.logger import logger
from app.utils.timezone import beijing_today

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioSummary)
async def list_portfolio(_=Depends(verify_api_key)):
    """获取持仓列表及盈亏汇总（股票/基金分开，数据源与分析页一致）"""
    async with async_session_factory() as session:
        items = await crud.get_portfolio(session)

    today = beijing_today()
    start = (today - datetime.timedelta(days=732)).isoformat()
    end = today.isoformat()

    stock_prices: dict[str, float] = {}
    fund_prices: dict[str, float] = {}
    stock_yesterday_prices: dict[str, float] = {}
    fund_yesterday_prices: dict[str, float] = {}

    for item in items:
        try:
            if item.asset_type == "fund":
                # 腾讯 → akshare ETF → akshare 开放基金（与分析页顺序一致）
                df = await get_market_data(
                    item.code, start, end,
                    tencent_adapter.fetch_fund_kline, asset_type="fund",
                )
                if df is None:
                    df = await get_market_data(
                        item.code, start, end,
                        akshare_adapter.fetch_etf_market_data, asset_type="fund",
                    )
                if df is None:
                    df = await get_market_data(
                        item.code, start, end,
                        akshare_adapter.fetch_fund_nav, asset_type="fund",
                    )
                target_prices = fund_prices
                target_yesterday = fund_yesterday_prices
            else:
                # 腾讯 → akshare → baostock（与分析页顺序一致）
                df = await get_market_data(
                    item.code, start, end,
                    tencent_adapter.fetch_stock_kline, asset_type="stock",
                )
                if df is None:
                    df = await get_market_data(
                        item.code, start, end,
                        akshare_adapter.fetch_stock_market_data, asset_type="stock",
                    )
                if df is None:
                    from app.services.adapters.baostock_adapter import fetch_market_data as baostock_fetch
                    df = await get_market_data(
                        item.code, start, end,
                        baostock_fetch, asset_type="stock",
                    )
                target_prices = stock_prices
                target_yesterday = stock_yesterday_prices

            if df is not None and not df.empty:
                closes = df["close"].dropna()
                target_prices[item.code] = float(closes.iloc[-1])
                if len(closes) >= 2:
                    target_yesterday[item.code] = float(closes.iloc[-2])
                else:
                    target_yesterday[item.code] = float(closes.iloc[-1])
        except Exception as e:
            logger.warning(f"[portfolio] 获取 {item.code} 价格失败: {e}")

    return await get_portfolio_summary(
        stock_prices, fund_prices,
        stock_yesterday_prices=stock_yesterday_prices,
        fund_yesterday_prices=fund_yesterday_prices,
    )


@router.post("/add")
async def add_to_portfolio(
    code: str,
    name: str,
    shares: float,
    cost_price: float,
    asset_type: str = Query(default="stock", description="stock | fund"),
    _=Depends(verify_api_key),
):
    """添加持仓（股票或基金）"""
    await add_position(code, name, shares, cost_price, asset_type)
    return {"status": "ok", "message": f"已添加 [{asset_type}] {code} {name}"}


@router.get("/by-code/{code}")
async def get_portfolio_item_by_code(
    code: str,
    asset_type: str = Query(default="stock", description="stock | fund"),
    _=Depends(verify_api_key),
):
    """通过代码获取持仓信息"""
    async with async_session_factory() as session:
        item = await crud.get_portfolio_by_code(session, code, asset_type)
    if not item:
        raise HTTPException(status_code=404, detail="持仓不存在")
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "asset_type": item.asset_type,
        "shares": item.shares,
        "cost_price": item.cost_price,
        "total_fees": item.total_fees,
        "added_at": item.added_at.isoformat(),
    }


@router.put("/{item_id}/shares")
async def update_portfolio_shares(
    item_id: int,
    shares: float = Query(...),
    cost_price: float = Query(default=0),
    _=Depends(verify_api_key),
):
    """直接更新持仓份额/成本"""
    async with async_session_factory() as session:
        item = await session.get(Portfolio, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="持仓不存在")
        item.shares = round(shares, 4)
        if cost_price > 0:
            item.cost_price = round(cost_price, 4)
        await session.commit()
    return {"status": "ok", "message": f"已更新持仓 #{item_id} 份额为 {shares}"}


@router.delete("/{item_id}")
async def remove_from_portfolio(item_id: int, _=Depends(verify_api_key)):
    """删除持仓"""
    await remove_position(item_id)
    return {"status": "ok", "message": f"已删除持仓 #{item_id}"}
