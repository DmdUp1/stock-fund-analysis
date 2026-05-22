"""SQLAlchemy 异步数据库引擎与会话"""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.utils.config import settings

# 确保数据库文件所在目录存在
_db_url = settings.DATABASE_URL
if _db_url.startswith("sqlite"):
    # sqlite+aiosqlite:///path/to/db
    db_path_str = _db_url.split("///", 1)[-1]
    if db_path_str:
        Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """创建所有表（如果不存在）"""
    from app.models.schemas import StockCache, Portfolio, Transaction, AnalysisRecord, BackupRecord  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
