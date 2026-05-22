"""仓库接口 —— 浏览历史分析记录"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import verify_api_key
from app.db.database import async_session_factory
from app.db import crud

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


@router.get("/groups")
async def list_warehouse_groups(
    asset_type: str = Query(default="", description="过滤类型: stock|fund"),
    _=Depends(verify_api_key),
):
    """按代码分组返回分析记录摘要"""
    async with async_session_factory() as session:
        groups = await crud.get_analysis_record_groups(session, asset_type=asset_type or None)
    return groups


@router.get("/by-code/{code}/all")
async def get_records_by_code(
    code: str,
    asset_type: str = Query(default="stock"),
    _=Depends(verify_api_key),
):
    """获取指定代码的所有历史分析记录"""
    async with async_session_factory() as session:
        records = await crud.get_analysis_records_by_code(session, code, asset_type)
    return [
        {
            "id": r.id,
            "code": r.code,
            "asset_type": r.asset_type,
            "summary": r.summary,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("")
async def list_warehouse(
    asset_type: str = Query(default="", description="过滤类型: stock|fund"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _=Depends(verify_api_key),
):
    """获取分析记录列表"""
    async with async_session_factory() as session:
        records = await crud.get_all_analysis_records(
            session, asset_type=asset_type or None, limit=limit, offset=offset,
        )
    return [
        {
            "id": r.id,
            "code": r.code,
            "asset_type": r.asset_type,
            "summary": r.summary,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/by-code/{code}")
async def get_latest_by_code(
    code: str,
    asset_type: str = Query(default="stock", description="stock|fund"),
    _=Depends(verify_api_key),
):
    """获取指定代码的最新一条分析记录"""
    async with async_session_factory() as session:
        records = await crud.get_latest_analysis(session, code, asset_type=asset_type, limit=1)
    if not records:
        return None
    r = records[0]
    return {
        "id": r.id,
        "code": r.code,
        "asset_type": r.asset_type,
        "summary": r.summary,
        "detail_json": r.detail_json,
        "created_at": r.created_at.isoformat(),
    }


@router.get("/{record_id}")
async def get_warehouse_item(record_id: int, _=Depends(verify_api_key)):
    """获取单条分析记录详情"""
    async with async_session_factory() as session:
        record = await crud.get_analysis_record_by_id(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": record.id,
        "code": record.code,
        "asset_type": record.asset_type,
        "summary": record.summary,
        "detail_json": record.detail_json,
        "created_at": record.created_at.isoformat(),
    }


@router.delete("/{record_id}")
async def delete_warehouse_item(record_id: int, _=Depends(verify_api_key)):
    """删除分析记录"""
    async with async_session_factory() as session:
        record = await crud.get_analysis_record_by_id(session, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        await crud.delete_analysis_record(session, record_id)
    return {"status": "ok", "message": f"已删除记录 #{record_id}"}
