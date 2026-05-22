"""API 安全依赖 —— Header API Key 验证"""

from fastapi import Header, HTTPException, status

from app.utils.config import settings


async def verify_api_key(x_api_key: str = Header("", alias="X-API-Key")) -> str:
    """验证 X-API-Key 请求头，返回 403 或 key。

    开发模式 (DEBUG=true) 下跳过验证，方便前端调试。
    """
    if not settings.API_KEY or settings.DEBUG:
        return "dev"
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key",
        )
    return x_api_key
