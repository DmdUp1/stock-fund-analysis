"""自动任务管理 —— 每日盘后分析 & 数据库备份"""

import datetime
import shutil
import json
from pathlib import Path

from app.utils.config import settings
from app.utils.logger import logger
from app.db import crud
from app.db.database import async_session_factory
from app.utils.timezone import beijing_now, beijing_today, beijing_from_timestamp


async def run_daily_analysis():
    """每日盘后分析任务（在自动分析路由中实现具体逻辑）"""
    logger.info("[auto_task] 开始每日盘后分析")
    # 具体分析逻辑由 API 层调用，此处仅触发标记
    # 实际业务：遍历持仓列表，逐一分析并保存
    try:
        async with async_session_factory() as session:
            items = await crud.get_portfolio(session)
            codes = [f"{item.code} - {item.name}" for item in items]
            summary = f"盘后分析完成，共 {len(items)} 只持仓"
            await crud.save_analysis(session, "AUTO", summary, json.dumps(codes, ensure_ascii=False))
        logger.info(f"[auto_task] {summary}")
    except Exception as e:
        logger.error(f"[auto_task] 分析任务失败: {e}")


async def backup_database():
    """备份数据库并清理超过 retention 天的旧备份"""
    db_path = settings.BASE_DIR / "financial_analyzer.db"
    if not db_path.exists():
        logger.warning("[backup] 数据库文件不存在，跳过备份")
        return

    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = beijing_today().isoformat()
    backup_path = settings.BACKUP_DIR / f"financial_analyzer_{today}.db"

    try:
        shutil.copy2(str(db_path), str(backup_path))
        file_size = backup_path.stat().st_size
        logger.info(f"[backup] 备份完成: {backup_path.name} ({file_size} bytes)")

        async with async_session_factory() as session:
            await crud.save_backup_record(session, str(backup_path), file_size)

        # 清理旧备份
        _cleanup_old_backups()
    except Exception as e:
        logger.error(f"[backup] 备份失败: {e}")


def _cleanup_old_backups():
    """清理超过 retention 天的旧备份文件"""
    cutoff = beijing_now() - datetime.timedelta(days=settings.BACKUP_RETENTION_DAYS)
    for f in settings.BACKUP_DIR.glob("financial_analyzer_*.db"):
        try:
            mtime = beijing_from_timestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                logger.info(f"[backup] 清理旧备份: {f.name}")
        except Exception as e:
            logger.warning(f"[backup] 清理失败 {f.name}: {e}")
