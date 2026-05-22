"""数据库 CRUD 操作"""

import datetime
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import StockCache, Portfolio, Transaction, AnalysisRecord, BackupRecord
from app.services.analysis_utils import parse_suggestion
from app.utils.timezone import beijing_now


# ── StockCache ───────────────────────────────────────────

async def get_cache(session: AsyncSession, cache_key: str) -> Optional[StockCache]:
    result = await session.execute(
        select(StockCache).where(
            StockCache.cache_key == cache_key,
            StockCache.expires_at > beijing_now(),
        )
    )
    return result.scalar_one_or_none()


async def set_cache(session: AsyncSession, cache_key: str, data_json: str, ttl_seconds: int = 3600):
    await session.execute(delete(StockCache).where(StockCache.cache_key == cache_key))
    entry = StockCache(
        cache_key=cache_key,
        data_json=data_json,
        expires_at=beijing_now() + datetime.timedelta(seconds=ttl_seconds),
    )
    session.add(entry)
    await session.commit()


# ── Portfolio ────────────────────────────────────────────

async def get_portfolio(session: AsyncSession, asset_type: Optional[str] = None) -> list[Portfolio]:
    stmt = select(Portfolio)
    if asset_type:
        stmt = stmt.where(Portfolio.asset_type == asset_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_portfolio_by_code(session: AsyncSession, code: str, asset_type: str) -> Optional[Portfolio]:
    result = await session.execute(
        select(Portfolio).where(Portfolio.code == code, Portfolio.asset_type == asset_type)
    )
    return result.scalar_one_or_none()


async def add_portfolio_item(
    session: AsyncSession, code: str, name: str,
    shares: float, cost_price: float, asset_type: str = "stock",
) -> Portfolio:
    item = Portfolio(code=code, name=name, shares=shares, cost_price=cost_price, asset_type=asset_type)
    session.add(item)
    await session.commit()
    return item


async def update_portfolio_item(
    session: AsyncSession, item: Portfolio, shares: float, cost_price: float, total_fees: float,
):
    item.shares = shares
    item.cost_price = cost_price
    item.total_fees = total_fees
    await session.commit()


async def remove_portfolio_item(session: AsyncSession, item_id: int):
    await session.execute(delete(Portfolio).where(Portfolio.id == item_id))
    await session.commit()


async def delete_transactions_by_portfolio(session: AsyncSession, portfolio_id: int):
    await session.execute(delete(Transaction).where(Transaction.portfolio_id == portfolio_id))
    await session.commit()


async def delete_analysis_records_by_code(session: AsyncSession, code: str, asset_type: str):
    await session.execute(
        delete(AnalysisRecord).where(
            AnalysisRecord.code == code,
            AnalysisRecord.asset_type == asset_type,
        )
    )
    await session.commit()


# ── Transaction ──────────────────────────────────────────

async def add_transaction(
    session: AsyncSession,
    portfolio_id: Optional[int], code: str, name: str, asset_type: str,
    tx_type: str, shares: float, price: float, amount: float, fee: float, tx_date: str,
) -> Transaction:
    tx = Transaction(
        portfolio_id=portfolio_id, code=code, name=name, asset_type=asset_type,
        tx_type=tx_type, shares=shares, price=price, amount=amount, fee=fee, tx_date=tx_date,
    )
    session.add(tx)
    await session.commit()
    return tx


async def get_transactions_by_portfolio(session: AsyncSession, portfolio_id: int) -> list[Transaction]:
    result = await session.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id).order_by(Transaction.tx_date.desc())
    )
    return list(result.scalars().all())


async def get_transaction_by_id(session: AsyncSession, tx_id: int) -> Optional[Transaction]:
    result = await session.execute(select(Transaction).where(Transaction.id == tx_id))
    return result.scalar_one_or_none()


async def update_transaction(
    session: AsyncSession, tx_id: int,
    tx_type: str, shares: float, price: float, amount: float, fee: float, tx_date: str,
) -> Optional[Transaction]:
    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        return None
    tx.tx_type = tx_type
    tx.shares = shares
    tx.price = price
    tx.amount = amount
    tx.fee = fee
    tx.tx_date = tx_date
    await session.commit()
    return tx


async def delete_transaction(session: AsyncSession, tx_id: int) -> bool:
    tx = await get_transaction_by_id(session, tx_id)
    if not tx:
        return False
    await session.delete(tx)
    await session.commit()
    return True


async def recalc_portfolio_from_transactions(session: AsyncSession, portfolio_id: int):
    """根据该持仓下所有交易重新计算 shares, cost_price, total_fees"""
    result = await session.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    txs: list[Transaction] = list(result.scalars().all())

    total_shares = 0.0
    total_cost = 0.0  # 买入总成本（不含手续费）
    total_fees = 0.0

    for tx in txs:
        total_fees += tx.fee
        if tx.tx_type in ("buy", "add"):
            total_shares += tx.shares
            total_cost += tx.amount
        elif tx.tx_type in ("reduce", "sell"):
            total_shares -= tx.shares
            if total_shares < 0:
                total_shares = 0

    avg_cost = (total_cost / total_shares) if total_shares > 0 else 0.0

    # 更新 Portfolio
    portfolio = await session.get(Portfolio, portfolio_id)
    if portfolio:
        portfolio.shares = round(total_shares, 4)
        portfolio.cost_price = round(avg_cost, 4)
        portfolio.total_fees = round(total_fees, 4)
        await session.commit()


# ── AnalysisRecord ───────────────────────────────────────

async def save_analysis(
    session: AsyncSession, code: str, summary: str,
    detail_json: str, asset_type: str = "stock",
):
    record = AnalysisRecord(code=code, summary=summary, detail_json=detail_json, asset_type=asset_type)
    session.add(record)
    await session.commit()
    return record


async def get_latest_analysis(
    session: AsyncSession, code: str,
    asset_type: Optional[str] = None, limit: int = 5,
) -> list[AnalysisRecord]:
    stmt = (
        select(AnalysisRecord)
        .where(AnalysisRecord.code == code)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(limit)
    )
    if asset_type:
        stmt = stmt.where(AnalysisRecord.asset_type == asset_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Warehouse (AnalysisRecord browsing) ──────────────────

async def get_all_analysis_records(
    session: AsyncSession,
    asset_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AnalysisRecord]:
    """获取分析记录列表（分页，可按资产类型过滤）"""
    stmt = select(AnalysisRecord).order_by(AnalysisRecord.created_at.desc()).limit(limit).offset(offset)
    if asset_type:
        stmt = stmt.where(AnalysisRecord.asset_type == asset_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_analysis_record_by_id(session: AsyncSession, record_id: int) -> Optional[AnalysisRecord]:
    result = await session.execute(select(AnalysisRecord).where(AnalysisRecord.id == record_id))
    return result.scalar_one_or_none()


async def delete_analysis_record(session: AsyncSession, record_id: int):
    await session.execute(delete(AnalysisRecord).where(AnalysisRecord.id == record_id))
    await session.commit()


async def get_analysis_record_groups(
    session: AsyncSession, asset_type: Optional[str] = None,
) -> list[dict]:
    """按 code 分组返回分析记录摘要，包含持仓信息"""
    stmt = select(
        AnalysisRecord.code,
        AnalysisRecord.asset_type,
        func.count(AnalysisRecord.id).label("record_count"),
        func.max(AnalysisRecord.created_at).label("latest_time"),
    )
    if asset_type:
        stmt = stmt.where(AnalysisRecord.asset_type == asset_type)
    stmt = stmt.group_by(AnalysisRecord.code, AnalysisRecord.asset_type).order_by(func.max(AnalysisRecord.created_at).desc())
    result = await session.execute(stmt)
    rows = result.all()

    groups = []
    for row in rows:
        # 取最新一条记录的摘要
        sub = await session.execute(
            select(AnalysisRecord.summary).where(
                AnalysisRecord.code == row.code,
                AnalysisRecord.asset_type == row.asset_type,
            ).order_by(AnalysisRecord.created_at.desc()).limit(1)
        )
        latest_summary = sub.scalar_one_or_none() or ""

        # 查询对应持仓信息
        port = await session.execute(
            select(Portfolio).where(
                Portfolio.code == row.code,
                Portfolio.asset_type == row.asset_type,
            ).limit(1)
        )
        portfolio = port.scalar_one_or_none()

        # 取最新一条分析的 detail_json 提取 AI 建议
        latest_rec = await session.execute(
            select(AnalysisRecord.detail_json).where(
                AnalysisRecord.code == row.code,
                AnalysisRecord.asset_type == row.asset_type,
            ).order_by(AnalysisRecord.created_at.desc()).limit(1)
        )
        detail_json_str = latest_rec.scalar_one_or_none()

        position_action, buy_zone, sell_zone, suggestion, suggestion_reason = parse_suggestion(
            detail_json_str, portfolio.shares if portfolio else 0, row.asset_type,
        )

        groups.append({
            "code": row.code,
            "asset_type": row.asset_type,
            "name": portfolio.name if portfolio else "",
            "record_count": row.record_count,
            "latest_summary": latest_summary,
            "latest_time": row.latest_time.isoformat() if row.latest_time else "",
            "portfolio_shares": portfolio.shares if portfolio else 0,
            "position_action": position_action,
            "buy_zone": buy_zone,
            "sell_zone": sell_zone,
            "suggestion": suggestion,
            "suggestion_reason": suggestion_reason,
        })
    return groups


async def get_analysis_records_by_code(
    session: AsyncSession, code: str, asset_type: str,
) -> list[AnalysisRecord]:
    result = await session.execute(
        select(AnalysisRecord).where(
            AnalysisRecord.code == code,
            AnalysisRecord.asset_type == asset_type,
        ).order_by(AnalysisRecord.created_at.desc())
    )
    return list(result.scalars().all())


# ── BackupRecord ─────────────────────────────────────────

async def save_backup_record(session: AsyncSession, file_path: str, file_size_bytes: int):
    record = BackupRecord(file_path=file_path, file_size_bytes=file_size_bytes)
    session.add(record)
    await session.commit()
    return record


async def get_backup_records(session: AsyncSession, limit: int = 20) -> list[BackupRecord]:
    result = await session.execute(
        select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
