"""持仓管理服务 —— 股票/基金分开统计"""

import datetime
import json
from typing import Optional

from sqlalchemy import select

from app.db import crud
from app.db.database import async_session_factory
from app.models.schemas import PortfolioItem, AssetPortfolioSummary, PortfolioSummary, AnalysisRecord
from app.services.analysis_utils import parse_suggestion


def _calc_holding_days(txs: list) -> int:
    """基于 FIFO 计算持仓中最早一笔买入距今的天数"""
    today = datetime.date.today()
    # 按交易日期升序排列
    sorted_txs = sorted(txs, key=lambda t: t.tx_date)
    # FIFO 队列: list of (date_str, shares)
    lots: list[tuple[str, float]] = []

    for tx in sorted_txs:
        if tx.tx_type in ("buy", "add"):
            lots.append((tx.tx_date, tx.shares))
        elif tx.tx_type in ("reduce", "sell"):
            remaining = tx.shares
            while remaining > 0 and lots:
                date_str, qty = lots[0]
                if qty <= remaining:
                    remaining -= qty
                    lots.pop(0)
                else:
                    lots[0] = (date_str, qty - remaining)
                    remaining = 0

    if not lots:
        return 0

    oldest_date_str = lots[0][0]
    try:
        oldest = datetime.date.fromisoformat(oldest_date_str)
        return (today - oldest).days
    except (ValueError, TypeError):
        return 0


def _build_item(item, price: float, yesterday_price: float = 0, holding_days: int = 0, total_fees: float = 0,
                position_action: str = "", buy_zone: str = "", sell_zone: str = "", suggestion: str = "",
                suggestion_reason: str = "") -> PortfolioItem:
    market_value = round(price * item.shares, 4)
    cost = round(item.cost_price * item.shares, 4)
    pl = round(market_value - cost, 4)
    pl_pct = round(((price - item.cost_price) / item.cost_price * 100) if item.cost_price > 0 else 0.0, 4)
    daily_change_pct = round(((price - yesterday_price) / yesterday_price * 100) if yesterday_price > 0 else 0.0, 4)
    net_asset = round(market_value - total_fees, 4)
    return PortfolioItem(
        id=item.id,
        code=item.code,
        name=item.name,
        asset_type=item.asset_type,
        shares=round(item.shares, 4),
        cost_price=round(item.cost_price, 4),
        current_price=round(price, 4),
        market_value=market_value,
        profit_loss=pl,
        profit_loss_pct=pl_pct,
        holding_days=holding_days,
        daily_change_pct=daily_change_pct,
        total_fees=round(total_fees, 4),
        net_asset=net_asset,
        position_action=position_action,
        buy_zone=buy_zone,
        sell_zone=sell_zone,
        suggestion=suggestion,
        suggestion_reason=suggestion_reason,
    )


def _summarize(items: list[PortfolioItem]) -> AssetPortfolioSummary:
    total_cost = round(sum(i.cost_price * i.shares for i in items), 4)
    total_mv = round(sum(i.market_value for i in items), 4)
    total_pl = round(total_mv - total_cost, 4)
    total_pl_pct = round(((total_mv / total_cost) - 1) * 100 if total_cost > 0 else 0.0, 4)
    total_fees = round(sum(i.total_fees for i in items), 4)
    return AssetPortfolioSummary(
        items=items,
        total_cost=total_cost,
        total_market_value=total_mv,
        total_profit_loss=total_pl,
        total_profit_loss_pct=total_pl_pct,
    )


def _parse_ai_suggestion(detail_json_str: str | None, shares: float, asset_type: str) -> tuple[str, str, str, str, str]:
    """委托 analysis_utils.parse_suggestion — 返回 (position_action, buy_zone, sell_zone, suggestion, reason)"""
    return parse_suggestion(detail_json_str, shares, asset_type)


async def get_portfolio_summary(
    stock_prices: dict[str, float],
    fund_prices: dict[str, float],
    stock_yesterday_prices: dict[str, float] | None = None,
    fund_yesterday_prices: dict[str, float] | None = None,
) -> PortfolioSummary:
    """获取持仓汇总（股票/基金分开），含昨日价用于计算涨跌幅"""
    if stock_yesterday_prices is None:
        stock_yesterday_prices = {}
    if fund_yesterday_prices is None:
        fund_yesterday_prices = {}

    async with async_session_factory() as session:
        all_items = await crud.get_portfolio(session)

    # 批量获取每只持仓的最新 AI 分析建议
    suggestion_cache: dict[str, tuple[str, str, str, str, str]] = {}
    async with async_session_factory() as session:
        for item in all_items:
            if item.code not in suggestion_cache:
                result = await session.execute(
                    select(AnalysisRecord.detail_json).where(
                        AnalysisRecord.code == item.code,
                        AnalysisRecord.asset_type == item.asset_type,
                    ).order_by(AnalysisRecord.created_at.desc()).limit(1)
                )
                detail_str = result.scalar_one_or_none()
                suggestion_cache[item.code] = _parse_ai_suggestion(detail_str, item.shares, item.asset_type)

    today = datetime.date.today()
    stock_items: list[PortfolioItem] = []
    fund_items: list[PortfolioItem] = []

    for item in all_items:
        pa, bz, sz, sug, reason = suggestion_cache.get(item.code, ("", "", "", "", ""))
        if item.asset_type == "fund":
            price = fund_prices.get(item.code, item.cost_price)
            yesterday_price = fund_yesterday_prices.get(item.code, price)
            total_fees = item.total_fees
            # FIFO 持有天数
            async with async_session_factory() as s:
                txs = await crud.get_transactions_by_portfolio(s, item.id)
            holding_days = _calc_holding_days(txs)
            fund_items.append(_build_item(item, price, yesterday_price, holding_days, total_fees, pa, bz, sz, sug, reason))
        else:
            price = stock_prices.get(item.code, item.cost_price)
            yesterday_price = stock_yesterday_prices.get(item.code, price)
            total_fees = item.total_fees
            async with async_session_factory() as s:
                txs = await crud.get_transactions_by_portfolio(s, item.id)
            holding_days = _calc_holding_days(txs)
            stock_items.append(_build_item(item, price, yesterday_price, holding_days, total_fees, pa, bz, sz, sug, reason))

    stocks = _summarize(stock_items)
    funds = _summarize(fund_items)

    total_cost = round(stocks.total_cost + funds.total_cost, 4)
    total_mv = round(stocks.total_market_value + funds.total_market_value, 4)
    total_pl = round(total_mv - total_cost, 4)
    total_pl_pct = round(((total_mv / total_cost) - 1) * 100 if total_cost > 0 else 0.0, 4)

    return PortfolioSummary(
        stocks=stocks,
        funds=funds,
        total_cost=total_cost,
        total_market_value=total_mv,
        total_profit_loss=total_pl,
        total_profit_loss_pct=total_pl_pct,
    )


async def add_position(code: str, name: str, shares: float, cost_price: float, asset_type: str = "stock"):
    async with async_session_factory() as session:
        return await crud.add_portfolio_item(session, code, name, shares, cost_price, asset_type)


async def remove_position(item_id: int):
    async with async_session_factory() as session:
        # 先获取持仓信息（用于删除分析记录）
        from sqlalchemy import select
        from app.models.schemas import Portfolio
        result = await session.execute(select(Portfolio).where(Portfolio.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            return
        code, asset_type = item.code, item.asset_type
        # 级联删除：交易记录 → 分析记录 → 持仓
        await crud.delete_transactions_by_portfolio(session, item_id)
        await crud.delete_analysis_records_by_code(session, code, asset_type)
        await crud.remove_portfolio_item(session, item_id)
