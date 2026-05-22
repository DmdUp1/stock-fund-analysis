"""应用配置——从.env加载所有配置项"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# 生产环境 —— 尝试加载 .env（优先级: exe同级 > exe上级）
if getattr(sys, "frozen", False):
    exe_dir = Path(os.path.dirname(sys.executable))
    for candidate in [exe_dir, exe_dir.parent]:
        env_file = candidate / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break


def _get_data_dir() -> Path:
    """用户数据目录（数据库、缓存、备份）"""
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable)) / "data"
    return BASE_DIR / "data"


class Settings:
    # 应用基础
    APP_NAME: str = "金融分析平台"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # API 安全
    API_KEY: str = os.getenv("API_KEY", "")
    API_KEY_NAME: str = "X-API-Key"

    # DeepSeek
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # 投资风格 —— 影响 AI 分析视角
    INVESTMENT_STYLE: str = os.getenv(
        "INVESTMENT_STYLE",
        "价值投资，中长期持有，重视安全边际",
    )

    # 数据库
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_get_data_dir()}/financial_analyzer.db",
    )

    # 缓存
    FILE_CACHE_DIR: Path = _get_data_dir() / "cache"
    FILE_CACHE_TTL: int = int(os.getenv("FILE_CACHE_TTL", "3600"))  # 默认1小时
    MEM_CACHE_TTL: int = int(os.getenv("MEM_CACHE_TTL", "300"))  # 默认5分钟
    MEM_CACHE_MAXSIZE: int = int(os.getenv("MEM_CACHE_MAXSIZE", "256"))

    # 备份
    BACKUP_DIR: Path = _get_data_dir() / "backups"
    BACKUP_RETENTION_DAYS: int = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))

    # 自动任务
    AUTO_ANALYSIS_HOUR: int = int(os.getenv("AUTO_ANALYSIS_HOUR", "18"))
    AUTO_ANALYSIS_MINUTE: int = int(os.getenv("AUTO_ANALYSIS_MINUTE", "30"))


settings = Settings()
