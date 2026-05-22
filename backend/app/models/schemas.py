"""SQLAlchemy ORM 模型 & Pydantic Schema"""

import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


# ── ORM 模型 ─────────────────────────────────────────────

class StockCache(Base):
    __tablename__ = "stock_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime)


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64))
    asset_type: Mapped[str] = mapped_column(String(8), default="stock")  # "stock" | "fund"
    shares: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[float] = mapped_column(Float, default=0.0)
    total_fees: Mapped[float] = mapped_column(Float, default=0.0)
    added_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("portfolio.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64), default="")
    asset_type: Mapped[str] = mapped_column(String(8), default="stock")
    tx_type: Mapped[str] = mapped_column(String(8))  # "buy" | "add" | "reduce" | "sell"
    shares: Mapped[float] = mapped_column(Float, default=0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    tx_date: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    asset_type: Mapped[str] = mapped_column(String(8), default="stock")
    summary: Mapped[str] = mapped_column(Text)
    detail_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(512))
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ── Pydantic Schema ──────────────────────────────────────

from pydantic import BaseModel


class MarketData(BaseModel):
    date: str
    open: float = 0.0
    close: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    code: str = ""


class MultiDimAnalysis(BaseModel):
    code: str
    name: str = ""
    asset_type: str = "stock"
    market_data: list[MarketData] = []
    technical_indicators: dict = {}
    price_percentile: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_label: str = ""
    fundamental: dict = {}
    style: str = ""
    cost_price: float = 0
    shares: float = 0


class AIReport(BaseModel):
    code: str
    name: str = ""
    asset_type: str = "stock"
    summary: str = ""
    style: str = ""
    technical_view: str = ""
    fundamental_view: str = ""
    sentiment_view: str = ""
    risk_warning: str = ""
    opportunity: str = ""
    advice: str = ""
    buy_zone: str = ""
    sell_zone: str = ""
    position_action: str = ""
    position_reason: str = ""
    strategy: str = ""
    personal_advice: str = ""
    market_advice: str = ""


class AnalysisResult(BaseModel):
    code: str
    name: str = ""
    asset_type: str = "stock"
    ai_report: AIReport
    market_data: list[MarketData] = []
    generated_at: str = ""


class PortfolioItem(BaseModel):
    id: int = 0
    code: str
    name: str
    asset_type: str = "stock"
    shares: float
    cost_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    holding_days: int = 0
    daily_change_pct: float = 0.0
    total_fees: float = 0.0
    net_asset: float = 0.0
    # AI suggestion from latest analysis
    position_action: str = ""
    buy_zone: str = ""
    sell_zone: str = ""
    suggestion: str = ""
    suggestion_reason: str = ""


class AssetPortfolioSummary(BaseModel):
    items: list[PortfolioItem] = []
    total_cost: float = 0.0
    total_market_value: float = 0.0
    total_profit_loss: float = 0.0
    total_profit_loss_pct: float = 0.0


class PortfolioSummary(BaseModel):
    stocks: AssetPortfolioSummary = AssetPortfolioSummary()
    funds: AssetPortfolioSummary = AssetPortfolioSummary()
    total_cost: float = 0.0
    total_market_value: float = 0.0
    total_profit_loss: float = 0.0
    total_profit_loss_pct: float = 0.0


class TransactionItem(BaseModel):
    id: int = 0
    portfolio_id: Optional[int] = None
    code: str = ""
    name: str = ""
    asset_type: str = "stock"
    tx_type: str = "buy"
    shares: float = 0.0
    price: float = 0.0
    amount: float = 0.0
    fee: float = 0.0
    tx_date: str = ""
    created_at: str = ""


class WarehouseGroup(BaseModel):
    code: str
    asset_type: str
    name: str = ""
    latest_summary: str = ""
    latest_time: str = ""
    record_count: int = 0


class AutoTaskStatus(BaseModel):
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    is_running: bool = False


class BackupInfo(BaseModel):
    file_path: str
    file_size_bytes: int
    created_at: str
