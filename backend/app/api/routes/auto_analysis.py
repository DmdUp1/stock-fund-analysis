"""自动分析 & 备份状态接口"""

import datetime

from fastapi import APIRouter, Depends

from app.api.deps import verify_api_key
from app.models.schemas import AutoTaskStatus, BackupInfo
from app.db import crud
from app.db.database import async_session_factory
from app.utils.timezone import beijing_now

router = APIRouter(prefix="/api/auto", tags=["auto"])


@router.get("/status", response_model=AutoTaskStatus)
async def get_auto_status(_=Depends(verify_api_key)):
    """获取自动任务状态"""
    # 从数据库中获取最近的自动分析记录和备份记录
    async with async_session_factory() as session:
        analyses = await crud.get_latest_analysis(session, "AUTO", limit=1)
        backups = await crud.get_backup_records(session, limit=1)

    last_run = analyses[0].created_at.isoformat() if analyses else None
    last_backup = backups[0].created_at.isoformat() if backups else None

    # 下次运行时间（默认为当日设定时间，若已过则次日）
    now = beijing_now()
    next_run = now.replace(
        hour=8, minute=0, second=0, microsecond=0,
    )
    if next_run <= now:
        next_run += datetime.timedelta(days=1)

    return AutoTaskStatus(
        last_run=last_backup or last_run,
        next_run=next_run.isoformat(),
        is_running=False,
    )


@router.get("/backups", response_model=list[BackupInfo])
async def list_backups(_=Depends(verify_api_key)):
    """获取备份记录"""
    async with async_session_factory() as session:
        records = await crud.get_backup_records(session, limit=20)
    return [
        BackupInfo(
            file_path=r.file_path,
            file_size_bytes=r.file_size_bytes,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
