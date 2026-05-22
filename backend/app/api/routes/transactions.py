"""交易接口 —— 交易驱动持仓管理"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import verify_api_key
from app.db.database import async_session_factory
from app.db import crud
from app.utils.logger import logger

router = APIRouter(prefix="/api/portfolio", tags=["transactions"])


class CreateTransactionRequest(BaseModel):
    code: str
    name: str = ""
    asset_type: str = "stock"
    tx_type: str = "buy"  # buy | add | reduce | sell
    shares: float
    price: float
    fee: float = 0.0
    tx_date: str = ""


class UpdateTransactionRequest(BaseModel):
    tx_type: str
    shares: float
    price: float
    fee: float = 0.0
    tx_date: str = ""


@router.post("/transaction")
async def create_transaction(req: CreateTransactionRequest, _=Depends(verify_api_key)):
    """新增交易，自动更新持仓"""
    amount = round(req.shares * req.price, 4)

    async with async_session_factory() as session:
        # 查找或创建持仓
        portfolio = await crud.get_portfolio_by_code(session, req.code, req.asset_type)

        if portfolio is None:
            # 首次买入，创建持仓
            portfolio = await crud.add_portfolio_item(
                session, req.code, req.name,
                shares=0, cost_price=0, asset_type=req.asset_type,
            )

        # 创建交易记录
        tx = await crud.add_transaction(
            session,
            portfolio_id=portfolio.id,
            code=req.code, name=req.name or portfolio.name,
            asset_type=req.asset_type,
            tx_type=req.tx_type,
            shares=req.shares, price=req.price,
            amount=amount, fee=req.fee,
            tx_date=req.tx_date or "",
        )

        # 重新汇总持仓
        await crud.recalc_portfolio_from_transactions(session, portfolio.id)

        logger.info(f"[transactions] 新增交易 {req.tx_type} {req.code} {req.shares}@{req.price}")

        return {
            "id": tx.id,
            "portfolio_id": portfolio.id,
            "code": tx.code,
            "name": tx.name,
            "asset_type": tx.asset_type,
            "tx_type": tx.tx_type,
            "shares": tx.shares,
            "price": tx.price,
            "amount": tx.amount,
            "fee": tx.fee,
            "tx_date": tx.tx_date,
            "created_at": tx.created_at.isoformat(),
        }


@router.get("/{portfolio_id}/transactions")
async def list_transactions(portfolio_id: int, _=Depends(verify_api_key)):
    """获取指定持仓的所有交易记录"""
    async with async_session_factory() as session:
        txs = await crud.get_transactions_by_portfolio(session, portfolio_id)
    return [
        {
            "id": tx.id,
            "portfolio_id": tx.portfolio_id,
            "code": tx.code,
            "name": tx.name,
            "asset_type": tx.asset_type,
            "tx_type": tx.tx_type,
            "shares": tx.shares,
            "price": tx.price,
            "amount": tx.amount,
            "fee": tx.fee,
            "tx_date": tx.tx_date,
            "created_at": tx.created_at.isoformat(),
        }
        for tx in txs
    ]


@router.put("/transaction/{tx_id}")
async def update_transaction(tx_id: int, req: UpdateTransactionRequest, _=Depends(verify_api_key)):
    """修改交易记录，重新汇总持仓"""
    amount = round(req.shares * req.price, 4)

    async with async_session_factory() as session:
        tx = await crud.update_transaction(
            session, tx_id,
            tx_type=req.tx_type, shares=req.shares,
            price=req.price, amount=amount,
            fee=req.fee, tx_date=req.tx_date,
        )
        if not tx:
            raise HTTPException(status_code=404, detail="交易记录不存在")

        if tx.portfolio_id:
            await crud.recalc_portfolio_from_transactions(session, tx.portfolio_id)

        return {
            "id": tx.id,
            "portfolio_id": tx.portfolio_id,
            "code": tx.code,
            "name": tx.name,
            "asset_type": tx.asset_type,
            "tx_type": tx.tx_type,
            "shares": tx.shares,
            "price": tx.price,
            "amount": tx.amount,
            "fee": tx.fee,
            "tx_date": tx.tx_date,
            "created_at": tx.created_at.isoformat(),
        }


@router.delete("/transaction/{tx_id}")
async def delete_transaction(tx_id: int, _=Depends(verify_api_key)):
    """删除交易记录，重新汇总持仓"""
    async with async_session_factory() as session:
        tx = await crud.get_transaction_by_id(session, tx_id)
        if not tx:
            raise HTTPException(status_code=404, detail="交易记录不存在")

        portfolio_id = tx.portfolio_id
        await crud.delete_transaction(session, tx_id)

        if portfolio_id:
            await crud.recalc_portfolio_from_transactions(session, portfolio_id)

    return {"status": "ok", "message": f"已删除交易 #{tx_id}"}
