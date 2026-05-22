"""分析接口 —— 单只股票或基金的全维度分析"""

import datetime
import json
import asyncio

from fastapi import APIRouter, Depends, Query

from app.api.deps import verify_api_key
from app.services.data_hub import get_market_data, get_fundamentals
from app.services.adapters import tencent_adapter, akshare_adapter
from app.services.analysis_engine import analyze_stock_technicals, analyze_fund_metrics
from app.services.sentiment_analyzer import analyze_sentiment
from app.services.ai_analyzer import generate_report
from app.models.schemas import MultiDimAnalysis, AnalysisResult, MarketData
from app.db.database import async_session_factory
from app.db import crud
from app.utils.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/{code}", response_model=AnalysisResult)
async def analyze_asset(
    code: str,
    asset_type: str = Query(default="stock", description="资产类型: stock | fund"),
    start: str = Query(default="", description="开始日期 YYYY-MM-DD"),
    end: str = Query(default="", description="结束日期 YYYY-MM-DD"),
    name: str = Query(default="", description="名称"),
    cost_price: float = Query(default=0, description="持仓成本价"),
    shares: float = Query(default=0, description="持仓数量"),
    _=Depends(verify_api_key),
):
    """对单只股票或基金进行全维度分析"""
    if not end:
        end = datetime.date.today().isoformat()
    if not start:
        start = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()

    logger.info(f"[analysis] 开始分析 [{asset_type}] {code} ({name}), 区间 {start} ~ {end}")

    if asset_type == "fund":
        return await _analyze_fund(code, name, start, end, cost_price, shares)
    else:
        return await _analyze_stock(code, name, start, end, cost_price, shares)


@router.get("/lookup/{code}")
async def lookup_asset_name(
    code: str,
    asset_type: str = Query(default="stock", description="stock | fund"),
    _=Depends(verify_api_key),
):
    """根据代码查询资产官方名称"""
    try:
        if asset_type == "fund":
            info = await tencent_adapter.fetch_fund_nav_realtime(code)
        else:
            info = await tencent_adapter.fetch_stock_realtime(code)
        if info and info.get("name"):
            return {"code": code, "name": info["name"]}
    except Exception as e:
        logger.warning(f"[analysis] 查询名称失败 {code}: {e}")
    return {"code": code, "name": ""}


async def _analyze_stock(code: str, name: str, start: str, end: str, cost_price: float = 0, shares: float = 0) -> AnalysisResult:
    """股票分析流程（腾讯财经优先）"""
    # 并行启动：基本面 + 新闻
    fund_task = asyncio.create_task(get_fundamentals(code, akshare_adapter.fetch_stock_fundamentals, asset_type="stock"))
    news_task = asyncio.create_task(akshare_adapter.fetch_stock_news(code))

    # 1. 行情（腾讯优先 → akshare → baostock）
    df = await get_market_data(code, start, end, tencent_adapter.fetch_stock_kline, asset_type="stock")
    if df is None:
        logger.info(f"[analysis] {code} 腾讯无数据，尝试 akshare")
        df = await get_market_data(code, start, end, akshare_adapter.fetch_stock_market_data, asset_type="stock")
    if df is None:
        logger.warning(f"[analysis] {code} ak也无数据，尝试 baostock")
        from app.services.adapters.baostock_adapter import fetch_market_data as baostock_fetch
        df = await get_market_data(code, start, end, baostock_fetch, asset_type="stock")

    # 1b. 转为 MarketData 列表
    market_data: list[MarketData] = []
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            market_data.append(MarketData(
                date=str(row.get("date", "")),
                open=float(row.get("open", 0)),
                close=float(row.get("close", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                volume=float(row.get("volume", 0)),
                code=code,
            ))

    # 2. 技术分析
    tech = analyze_stock_technicals(df) if df is not None else {}
    price_percentile = tech.get("price_percentile_252d")

    # 等待并行任务
    fundamentals = await fund_task
    news = await news_task

    # 4. 新闻 & 情感
    sentiment = await analyze_sentiment(news)

    # 5. 组装 + AI
    multi = MultiDimAnalysis(
        code=code, name=name, asset_type="stock",
        market_data=market_data,
        technical_indicators=tech, price_percentile=price_percentile,
        sentiment_score=sentiment.get("score"), sentiment_label=sentiment.get("label", "中性"),
        fundamental=fundamentals or {}, style=settings.INVESTMENT_STYLE,
        cost_price=cost_price, shares=shares,
    )
    ai_report = await generate_report(multi)

    result = AnalysisResult(
        code=code, name=name, asset_type="stock",
        market_data=market_data,
        ai_report=ai_report, generated_at=datetime.datetime.now().isoformat(),
    )

    # 保存到仓库
    await _save_analysis(result)
    return result


async def _analyze_fund(code: str, name: str, start: str, end: str, cost_price: float = 0, shares: float = 0) -> AnalysisResult:
    """基金分析流程（腾讯财经优先）"""
    # 并行启动：基金档案 + 新闻
    fund_info_task = asyncio.create_task(get_fundamentals(code, akshare_adapter.fetch_fund_info, asset_type="fund"))
    news_task = asyncio.create_task(akshare_adapter.fetch_fund_news(code))

    # 1. 净值数据（腾讯优先 → akshare ETF → akshare 开放基金）
    df = await get_market_data(code, start, end, tencent_adapter.fetch_fund_kline, asset_type="fund")
    if df is None:
        logger.info(f"[analysis] 基金 {code} 腾讯无净值，尝试 akshare ETF")
        df = await get_market_data(code, start, end, akshare_adapter.fetch_etf_market_data, asset_type="fund")
    if df is None:
        df = await get_market_data(code, start, end, akshare_adapter.fetch_fund_nav, asset_type="fund")

    # 1b. 转为 MarketData 列表
    market_data: list[MarketData] = []
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            market_data.append(MarketData(
                date=str(row.get("date", "")),
                open=float(row.get("open", 0)) if row.get("open") else float(row.get("close", 0)),
                close=float(row.get("close", 0)),
                high=float(row.get("high", 0)) if row.get("high") else float(row.get("close", 0)),
                low=float(row.get("low", 0)) if row.get("low") else float(row.get("close", 0)),
                volume=float(row.get("volume", 0)),
                code=code,
            ))

    # 2. 净值分析
    tech = analyze_fund_metrics(df) if df is not None else {}

    # 等待并行任务
    fund_info = await fund_info_task
    news = await news_task

    # 4. 新闻 & 情感
    sentiment = await analyze_sentiment(news)

    multi = MultiDimAnalysis(
        code=code, name=name, asset_type="fund",
        market_data=market_data,
        technical_indicators=tech,
        sentiment_score=sentiment.get("score"), sentiment_label=sentiment.get("label", "中性"),
        fundamental=fund_info or {}, style=settings.INVESTMENT_STYLE,
        cost_price=cost_price, shares=shares,
    )
    ai_report = await generate_report(multi)

    result = AnalysisResult(
        code=code, name=name, asset_type="fund",
        market_data=market_data,
        ai_report=ai_report, generated_at=datetime.datetime.now().isoformat(),
    )

    # 保存到仓库
    await _save_analysis(result)
    return result


async def _save_analysis(result: AnalysisResult):
    """将分析结果保存到数据库仓库"""
    try:
        async with async_session_factory() as session:
            summary = result.ai_report.summary or f"{result.code} 分析完成"
            detail = result.model_dump_json()
            await crud.save_analysis(
                session, result.code, summary, detail, asset_type=result.asset_type,
            )
    except Exception as e:
        logger.warning(f"[analysis] 保存分析记录失败: {e}")
