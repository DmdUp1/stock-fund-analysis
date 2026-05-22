# 金融分析平台 —— 开发与维护指南

> **适用对象**：零基础开发者 / 接手项目的维护人员
> **技术栈**：Python FastAPI（后端）+ Vue 3 + TypeScript（前端）
> **项目作用**：股票/基金的持仓管理、AI 智能分析、交易记录追踪

---

## 目录

1. [项目整体架构](#1-项目整体架构)
2. [快速启动](#2-快速启动)
3. [项目目录总览](#3-项目目录总览)
4. [后端详解](#4-后端详解)
5. [前端详解](#5-前端详解)
6. [数据获取（爬虫 / API）](#6-数据获取爬虫--api)
7. [数据库创建与操作](#7-数据库创建与操作)
8. [Agent（AI 分析）全流程](#8-agentai-分析全流程)
9. [常见开发任务](#9-常见开发任务)
10. [常见问题排查](#10-常见问题排查)

---

## 1. 项目整体架构

```
用户浏览器 (Vue 3 SPA)
       │  http://localhost:5173
       ▼
Vite 开发服务器 (端口 5173)
       │  /api/* 代理到后端
       ▼
FastAPI 后端 (端口 8000)
       │
       ├── 腾讯财经 API (实时行情/K线)
       ├── akshare (基本面/基金净值/新闻)
       ├── baostock (备用行情)
       ├── DeepSeek API (AI 分析)
       └── SQLite 数据库 (持仓/交易/分析记录)
```

**数据流简图**：

```
用户操作 → Vue 前端 → API 请求 → FastAPI 路由
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼            ▼
                      数据适配器    AI 分析器    数据库 CRUD
                   (腾讯/akshare)   (DeepSeek)   (SQLite)
                          │            │            │
                          ▼            ▼            ▼
                      返回结果  ←  组装响应  ←  读写数据
                          │
                          ▼
                     前端展示
```

---

## 2. 快速启动

### 环境要求

- Python 3.11+
- Node.js 20+ / 22+
- （可选）DeepSeek API Key，在 `backend/.env` 中配置

### 2.1 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（仅首次）
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建配置文件
# 在 backend/ 下创建 .env 文件（参考下方配置说明）

# 5. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 http://localhost:8000/api/health 确认服务正常（返回 `{"status":"ok"}`）。

### 2.2 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

启动后访问 http://localhost:5173 即可使用。

### 2.3 `.env` 配置文件

在 `backend/` 目录下创建 `.env` 文件：

```ini
# API 安全（可选，留空则不校验）
API_KEY=your_api_key_here

# DeepSeek（AI 分析必需）
DEEPSEEK_API_KEY=sk-your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 投资风格（影响 AI 分析视角）
INVESTMENT_STYLE=价值投资，中长期持有，重视安全边际

# 数据库路径（默认 SQLite）
# DATABASE_URL=sqlite+aiosqlite:///./data/financial_analyzer.db

# 调试模式（true 时跳过 API Key 验证）
DEBUG=true

# 自动任务时间（24小时制）
AUTO_ANALYSIS_HOUR=18
AUTO_ANALYSIS_MINUTE=30
```

---

## 3. 项目目录总览

```
股票基金分析/
│
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # 应用入口（FastApp + CORS + 定时任务）
│   │   ├── api/
│   │   │   ├── deps.py               # API 依赖（API Key 验证）
│   │   │   └── routes/
│   │   │       ├── analysis.py       # 分析接口（核心：股票/基金全维度分析）
│   │   │       ├── portfolio.py      # 持仓接口（列表/增删/汇总）
│   │   │       ├── transactions.py   # 交易接口（增删改查）
│   │   │       ├── warehouse.py      # 仓库接口（浏览历史分析记录）
│   │   │       └── auto_analysis.py  # 自动任务接口（状态/备份查询）
│   │   ├── services/
│   │   │   ├── data_hub.py           # 三级缓存数据中枢（内存→文件→数据源）
│   │   │   ├── portfolio_manager.py  # 持仓管理（汇总/FIFO持有天数计算）
│   │   │   ├── analysis_engine.py    # 分析引擎（技术指标/基金净值指标）
│   │   │   ├── ai_analyzer.py        # AI 分析器（调用 DeepSeek）
│   │   │   ├── sentiment_analyzer.py # 情感分析（新闻标题 NLP 打分）
│   │   │   ├── analysis_utils.py     # 分析结果解析工具
│   │   │   ├── auto_task_manager.py  # 自动任务管理（定时分析/备份）
│   │   │   └── adapters/             # 数据源适配器
│   │   │       ├── tencent_adapter.py    # 腾讯财经 API
│   │   │       ├── akshare_adapter.py    # akshare 数据
│   │   │       └── baostock_adapter.py   # baostock 数据
│   │   ├── models/
│   │   │   └── schemas.py            # ORM 模型 + Pydantic 数据模型
│   │   ├── db/
│   │   │   ├── database.py           # SQLAlchemy 引擎与会话
│   │   │   └── crud.py               # 数据库 CRUD 操作
│   │   └── utils/
│   │       ├── config.py             # 配置（从.env加载）
│   │       ├── logger.py             # 日志配置
│   │       └── timezone.py           # 北京时间工具
│   ├── data/                         # 运行时数据（自动创建）
│   │   ├── financial_analyzer.db     # SQLite 数据库
│   │   ├── cache/                    # 数据缓存
│   │   └── backups/                  # 数据库备份
│   ├── requirements.txt
│   └── .env                          # 配置文件（需手动创建）
│
├── frontend/                         # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── main.ts                   # Vue 应用入口
│   │   ├── App.vue                   # 根组件
│   │   ├── router/
│   │   │   └── index.ts              # 路由配置
│   │   ├── views/
│   │   │   ├── StockPortfolioView.vue    # 股票持仓页面
│   │   │   ├── FundPortfolioView.vue     # 基金持仓页面
│   │   │   ├── WarehouseView.vue         # 分析仓库页面
│   │   │   └── WarehouseDetailView.vue   # 分析详情页面
│   │   ├── services/
│   │   │   └── api.ts                # API 请求封装
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript 类型定义
│   │   └── style.css                 # 全局样式（暗色主题）
│   ├── vite.config.ts                # Vite 配置（代理/端口）
│   └── package.json
│
└── DEVELOPMENT.md                    # 本文件
```

---

## 4. 后端详解

### 4.1 应用入口 [main.py](backend/app/main.py)

FastAPI 应用的生命周期管理：

```
启动 → lifespan 函数:
  1. 创建 data/cache/backups 目录
  2. 初始化数据库表（init_db）
  3. 启动 APScheduler 定时任务
     - 每日盘后分析（默认 18:30）
     - 每日数据库备份（默认 23:00）
  4. 注册 API 路由
  5. 注册 SPA 静态文件服务（生产环境）
```

**关键点**：
- 开发时前端用 Vite dev server（5173），后端需要 CORS 放行
- 生产环境后端直接托管前端构建产物（`frontend/dist/`）
- 运行时配置通过 `/api/client-config` 注入前端

### 4.2 API 路由层

所有路由使用 `APIRouter`，通过 `verify_api_key` 依赖保护：

| 路由文件 | 前缀 | 功能 |
|---------|------|------|
| [analysis.py](backend/app/api/routes/analysis.py) | `/api/analysis` | 股票/基金全维度分析 |
| [portfolio.py](backend/app/api/routes/portfolio.py) | `/api/portfolio` | 持仓列表/增删 |
| [transactions.py](backend/app/api/routes/transactions.py) | `/api/portfolio` | 交易记录增删改查 |
| [warehouse.py](backend/app/api/routes/warehouse.py) | `/api/warehouse` | 分析仓库浏览 |
| [auto_analysis.py](backend/app/api/routes/auto_analysis.py) | `/api/auto` | 自动任务状态/备份列表 |

**路由编写规范**：
- 每个路由函数标明 `response_model` 确保返回格式一致
- 使用 `Depends(verify_api_key)` 进行 API Key 验证
- 异步函数（`async def`）操作数据库时使用 `async with async_session_factory()`

### 4.3 服务层

#### 数据中枢 [data_hub.py](backend/app/services/data_hub.py)

三级缓存架构，避免重复请求外部 API：

```
get_market_data() 流程:
  1. 检查内存缓存 (cachetools TTLCache, 5分钟)
  2. 检查文件缓存 (pickle 序列化, 1小时)
  3. 调用数据源适配器（腾讯 → akshare → baostock）
  4. 结果写入内存 + 文件缓存
```

#### 分析引擎 [analysis_engine.py](backend/app/services/analysis_engine.py)

纯 pandas/numpy 计算，不依赖外部服务：

| 函数 | 计算指标 |
|------|---------|
| `analyze_stock_technicals()` | MA5/10/20/60, RSI, MACD, 布林带, 波动率, 价格分位 |
| `analyze_fund_metrics()` | 净值/累计净值, 累计收益率, 最大回撤, 波动率, 净值分位 |

#### 持仓管理 [portfolio_manager.py](backend/app/services/portfolio_manager.py)

- `get_portfolio_summary()`：汇总所有持仓的盈亏、市值、日涨跌幅
- `add_position()` / `remove_position()`：增删持仓（级联删除交易和分析记录）
- `_calc_holding_days()`：基于 FIFO 计算实际持仓天数

#### AI 分析器 [ai_analyzer.py](backend/app/services/ai_analyzer.py)

调用 DeepSeek API 生成分析报告：

```
generate_report() 流程:
  1. 根据资产类型（股票/基金）构建不同 prompt
  2. 调用 DeepSeek chat.completions API
  3. 解析 JSON 响应 → AIReport 对象
  4. API 失败时降级到规则报告（_fallback_report）
```

#### 情感分析 [sentiment_analyzer.py](backend/app/services/sentiment_analyzer.py)

基于词库匹配的简单 NLP：对新闻标题扫描正面/负面关键词，计算综合得分。

---

## 5. 前端详解

### 5.1 页面路由

| 路径 | 路由 | 视图文件 | 功能 |
|------|------|---------|------|
| `/stocks` | 股票持仓 | [StockPortfolioView.vue](frontend/src/views/StockPortfolioView.vue) | 股票列表+分析 |
| `/funds` | 基金持仓 | [FundPortfolioView.vue](frontend/src/views/FundPortfolioView.vue) | 基金列表+分析 |
| `/warehouse` | 分析仓库 | [WarehouseView.vue](frontend/src/views/WarehouseView.vue) | 历史分析记录 |
| `/warehouse/:id` | 仓库详情 | [WarehouseDetailView.vue](frontend/src/views/WarehouseDetailView.vue) | 单条记录详情 |

### 5.2 API 请求 [api.ts](frontend/src/services/api.ts)

统一的 `request<T>()` 封装：
- 自动注入 API Key（运行时配置 → 环境变量）
- 统一错误处理（非 200 状态抛异常）
- 所有 API 调用通过 `api` 对象暴露

**添加新 API** 的步骤：
1. 在 `api` 对象中添加方法
2. 调用 `request<T>(url, options)`
3. 返回类型定义在 `types/index.ts` 中

### 5.3 类型定义 [types/index.ts](frontend/src/types/index.ts)

前后端类型一一对应：
- `AnalysisResult` / `AIReport` ← 对应 Python `AnalysisResult` / `AIReport`
- `PortfolioItem` / `PortfolioSummary` ← 对应 Python 同名类
- `WarehouseItem` / `WarehouseGroup` ← 分析仓库记录
- `TransactionItem` ← 交易记录

### 5.4 关键功能实现

**持仓页面的分析流程**（以 `StockPortfolioView.vue` 为例）：

```
点击"分析"按钮 → openAnalysis():
  1. 设置 loading，从仓库查询最新分析记录
  2. 如果有缓存：直接加载到 modalItem（不重新分析）
  3. 如果没有缓存：调用 api.analyzeAsset() 触发全量分析
  4. 加载分析报告到模态框中展示

点击"刷新分析"按钮 → refreshAnalysis():
  1. 强制调用 api.analyzeAsset() 重新分析
  2. 传递持仓成本、份额、持有天数等上下文
  3. 更新模态框展示
```

**交易记录功能**：
- 创建交易时自动更新对应持仓的份额/成本（FIFO）
- 持仓列表展开后加载交易记录（`txCache` 缓存）
- 支持修改和删除交易记录，自动重新汇总持仓

---

## 6. 数据获取（爬虫 / API）

项目使用**三个数据源**，按优先级自动切换：

### 6.1 腾讯财经 API（首选）

适合：股票 K 线、实时行情、基金实时净值

| 接口 | 函数 | 用途 |
|------|------|------|
| 股票日线K线 | `tencent_adapter.fetch_stock_kline()` | 技术分析基础数据 |
| 股票实时行情 | `tencent_adapter.fetch_stock_realtime()` | 持仓当前价 |
| 基金实时净值 | `tencent_adapter.fetch_fund_nav_realtime()` | 基金名称查询 |
| 基金持仓 | `tencent_adapter.fetch_fund_holdings()` | 基金持仓结构 |

**实现方式**：HTTP GET 请求腾讯财经公开 API，返回 JSON 数据解析为 DataFrame。

### 6.2 akshare（备选 + 扩展数据）

适合：基本面、基金净值、新闻

| 接口 | 函数 | 用途 |
|------|------|------|
| A 股日线 | `akshare_adapter.fetch_stock_market_data()` | 股票 K 线备选 |
| 股票基本面 | `akshare_adapter.fetch_stock_fundamentals()` | PE/PB/ROE |
| 股票新闻 | `akshare_adapter.fetch_stock_news()` | 情感分析 |
| 基金净值 | `akshare_adapter.fetch_fund_nav()` | 开放基金净值 |
| ETF行情 | `akshare_adapter.fetch_etf_market_data()` | ETF 替代数据 |
| 基金信息 | `akshare_adapter.fetch_fund_info()` | 基金经理/规模 |

**实现方式**：调用 `akshare` Python 库（底层爬取东方财富等财经网站）。

> **注意**：akshare 的 Python 版本要求为 **Python 3.11**（当前版本限制），未来可能需要升级。

### 6.3 baostock（最后备选）

适合：腾讯和 akshare 都失败时的股票 K 线数据。

**实现方式**：`baostock` 库，需要先 `bs.login()` 再查询。

### 6.4 数据获取流程图

```
股票 K 线获取:
  腾讯财经 API ──成功──→ 返回 DataFrame
     │失败
     ▼
  akshare ──成功──→ 返回 DataFrame
     │失败
     ▼
  baostock ──成功──→ 返回 DataFrame

基金净值获取:
  腾讯财经 API（基金接口受限，通常返回 None）
     │失败
     ▼
  akshare ETF ──成功──→ 返回 DataFrame
     │失败
     ▼
  akshare 开放基金净值 ──成功──→ 返回 DataFrame
```

### 6.5 缓存机制

数据经过**三级缓存**减少重复请求：

1. **内存缓存**：`cachetools.TTLCache`，默认 5 分钟
2. **文件缓存**：pickle/JSON 文件，默认 1 小时
3. **数据源**：实时获取

缓存通过 `data_hub.py` 的 `get_market_data()` / `get_fundamentals()` 统一管理。

---

## 7. 数据库创建与操作

### 7.1 数据库选择

使用 **SQLite**（通过 `aiosqlite` 异步驱动），数据库文件位于 `backend/data/financial_analyzer.db`。

表结构（ORM 定义在 [models/schemas.py](backend/app/models/schemas.py)）：

| 表名 | 模型类 | 用途 | 关键字段 |
|------|--------|------|---------|
| `stock_cache` | `StockCache` | 数据缓存 | cache_key, data_json, expires_at |
| `portfolio` | `Portfolio` | 持仓记录 | code, name, shares, cost_price |
| `transactions` | `Transaction` | 交易记录 | portfolio_id, tx_type, shares, price |
| `analysis_records` | `AnalysisRecord` | AI 分析记录 | code, summary, detail_json |
| `backup_records` | `BackupRecord` | 备份记录 | file_path, file_size_bytes |

### 7.2 ORM 模型说明

所有模型继承 `Base`（来自 `database.py`），使用 SQLAlchemy 2.0 声明式映射：

```python
class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64))
    shares: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[float] = mapped_column(Float, default=0.0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now)
```

**时间字段说明**：所有 `created_at` / `added_at` 字段使用北京时间（UTC+8），通过 `app.utils.timezone.beijing_now()` 生成，参见 [timezone.py](backend/app/utils/timezone.py)。

### 7.3 数据库初始化

在 `backend/app/db/database.py` 中：

```python
async def init_db():
    """创建所有表（如果不存在）"""
    from app.models.schemas import StockCache, Portfolio, Transaction, AnalysisRecord, BackupRecord
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- 应用启动时自动调用（`main.py` lifespan）
- 如果表已存在则跳过（`create_all` 幂等）
- 新增字段需要手动执行 **ALTER TABLE** 或删表重建

### 7.4 CRUD 操作

所有数据库操作集中在 [crud.py](backend/app/db/crud.py)，按模块组织：

**常用函数**：

```python
# 持仓
get_portfolio(session)                    # 获取所有持仓
add_portfolio_item(session, code, name, shares, cost_price, asset_type)
remove_portfolio_item(session, item_id)
update_portfolio_item(session, item, shares, cost_price, total_fees)

# 交易
add_transaction(session, portfolio_id, code, name, asset_type, tx_type, shares, price, amount, fee, tx_date)
get_transactions_by_portfolio(session, portfolio_id)
delete_transaction(session, tx_id)
recalc_portfolio_from_transactions(session, portfolio_id)  # 重新汇总持仓

# 分析记录
save_analysis(session, code, summary, detail_json, asset_type)
get_latest_analysis(session, code, asset_type, limit=5)
delete_analysis_record(session, record_id)
```

### 7.5 新增数据库字段的步骤

```python
# 1. 在 models/schemas.py 的对应模型中添加字段
class Portfolio(Base):
    ...
    new_field: Mapped[str] = mapped_column(String(64), default="")

# 2. 重启后端，SQLite 会自动添加字段（ALTER TABLE ADD COLUMN）
#    注意：SQLite 的 ALTER TABLE 不支持所有操作
#    复杂变更需要导出 → 重建表 → 导入
```

---

## 8. Agent（AI 分析）全流程

### 8.1 完整调用链

```
StockPortfolioView.vue
  └─ 用户点击"分析"按钮
      └─ openAnalysis()
          ├─ 1. 查询分析仓库 (api.getWarehouseLatest)
          │     ├─ 有缓存 → 直接展示，不重新分析
          │     └─ 无缓存 → 进入第2步
          │
          └─ 2. 调用 api.analyzeAsset(code, ...)
                └─ GET /api/analysis/{code}
                      └─ analysis.py: analyze_asset()
                            │
                            ├─ 并行启动:
                            │   ├─ get_fundamentals() → akshare 基本面
                            │   └─ akshare_adapter.fetch_stock_news()
                            │
                            ├─ get_market_data() → 3级缓存 → K线数据
                            │     ├─ 腾讯财经 (优先)
                            │     ├─ akshare (备选)
                            │     └─ baostock (最后备选)
                            │
                            ├─ analyze_stock_technicals(df)
                            │     └─ 计算 MA/RSI/MACD/布林带/波动率/分位
                            │
                            ├─ analyze_sentiment(news)
                            │     └─ 词库匹配 → 得分 + 标签
                            │
                            ├─ MultiDimAnalysis (组装所有数据)
                            │
                            ├─ generate_report(multi)
                            │     └─ 调用 DeepSeek API
                            │         ├─ _build_stock_prompt() / _build_fund_prompt()
                            │         ├─ API 调用 → JSON 响应
                            │         └─ 失败 → _fallback_report() 规则降级
                            │
                            └─ _save_analysis() → 存入 analysis_records 表
```

### 8.2 Prompt 工程

AI prompt 位于 `ai_analyzer.py` 的两个构建函数：

- `_build_stock_prompt()`：股票分析 prompt，包含技术面 + 基本面 + 持仓上下文
- `_build_fund_prompt()`：基金分析 prompt，包含净值表现 + 基金档案 + 持仓上下文

**Prompt 结构**：
1. 角色设定（资深分析师，指定投资风格）
2. 资产信息（代码、名称）
3. 技术面数据（均线/RSI/MACD/布林带/波动率/价格分位）
4. 基本面数据（PE/PB/ROE 等）
5. 市场情绪（标签 + 得分）
6. 持仓上下文（成本/份额/盈亏/持有天数）
7. JSON 输出格式要求（19 个字段，包含 position_action 的枚举约束）

**重要**：修改 AI 输出字段时，需要同步更新：
1. Python `AIReport` 模型（[schemas.py](backend/app/models/schemas.py)）
2. 前端 `AIReport` 接口（[types/index.ts](frontend/src/types/index.ts)）
3. Prompt 中的 JSON 格式要求
4. `_fallback_report()` 的降级逻辑

### 8.3 持仓上下文传递

AI 分析需要知道用户的持仓情况才能给出个性化建议。上下文传递链：

```
前端 PortfolioItem.holding_days
  → api.analyzeAsset(holdingDays)
    → GET /api/analysis/{code}?holding_days=X
      → analysis.py: _analyze_stock(holding_days=X)
        → tech["holding_days"] = X
          → MultiDimAnalysis(technical_indicators=tech)
            → generate_report() → AIReport
              → Prompt 中包含"持有时长: X天"
```

### 8.4 分析结果解析 [analysis_utils.py](backend/app/services/analysis_utils.py)

AI 返回的 JSON 经过 `parse_suggestion()` 解析：

```
AI 返回 JSON
  → 提取 position_action（标准化值：加仓/减仓/持有观望/定投/清仓/观望）
  → _calc_suggestion() 计算建议份额
  → 生成展示用的 suggestion 标签
```

**旧数据兼容**：`_heuristic_suggestion()` 处理旧格式的 AI 分析记录，通过关键词匹配提取操作建议。

---

## 9. 常见开发任务

### 9.1 新增 API 端点

```
后端修改:
  1. 在对应 routes 文件中添加路由函数
  2. 如果需要新数据模型，在 schemas.py 中添加 Pydantic 模型
  3. 如果需要数据库操作，在 crud.py 中添加函数
  4. 在 main.py 中注册路由（如果新建了 router 文件）

前端修改:
  1. 在 types/index.ts 中添加 TypeScript 类型
  2. 在 api.ts 中添加 API 调用方法
  3. 在 views 中调用并展示数据
```

### 9.2 新增数据源适配器

```python
# 1. 在 adapters/ 目录下新建文件，如 my_adapter.py
# 2. 实现 async 函数，返回 pd.DataFrame 或 dict
# 3. 在 data_hub.py 的 get_market_data() 调用链中添加
# 4. 或在 analysis.py 的路由中直接调用

# 适配器函数签名约定:
async def fetch_something(code: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """返回 DataFrame，必须包含 date, close 列"""
    ...
```

### 9.3 构建生产版本

```bash
# 1. 构建前端
cd frontend
npm run build-only    # 生成到 frontend/dist/

# 2. 运行后端（自动托管前端静态文件）
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 访问 http://localhost:8000 即可使用
```

### 9.4 前端开发规范

- 使用 `<script setup lang="ts">` 组合式 API
- 全局样式在 `style.css`，组件样式用 `<style scoped>`
- 所有 API 调用通过 `api.ts` 封装
- 添加新页面时在 `router/index.ts` 注册路由
- TypeScript 类型先在 `types/index.ts` 定义

### 9.5 修改样式

全局 CSS 变量定义在 [style.css](frontend/src/style.css) 的 `:root` 中：

```css
:root {
  --bg: #0a0c14;           /* 背景色 */
  --bg-card: ...            /* 卡片背景 */
  --accent: #4fc3f7;       /* 主题色（亮蓝） */
  --green: #f87171;        /* 涨/盈利（中国红涨绿跌） */
  --red: #34d399;           /* 跌/亏损 */
  --radius: 14px;           /* 圆角 */
  ...
}
```

**重要颜色约定**（中国股市惯例）：
- 红色 (`--green`) = 上涨/盈利
- 绿色 (`--red`) = 下跌/亏损

---

## 10. 常见问题排查

### 后端启动报错

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError` | 未安装依赖 | `pip install -r requirements.txt` |
| `Address already in use` | 端口被占用 | 更换端口或 `netstat -ano` 查找进程 |
| `DEEPSEEK_API_KEY not set` | 未配置 API Key | 在 `.env` 中配置（分析功能不可用时可用降级报告） |
| `f-string backslash` | Python 版本过低 | 使用 Python 3.11+ |

### 前端启动报错

| 错误 | 原因 | 解决 |
|------|------|------|
| `npm ERR!` | 依赖未安装 | `npm install` |
| `Port 5173 in use` | 端口被占用 | `npx kill-port 5173` 或修改 vite.config.ts |
| `TypeScript error` | 类型不匹配 | 运行 `npx vue-tsc --noEmit` 查看具体错误 |

### 数据获取失败

| 现象 | 原因 | 解决 |
|------|------|------|
| 股票无数据 | 休市/代码错误/腾讯接口限流 | 自动切换到 akshare → baostock |
| 基金无数据 | 腾讯不支持基金K线 | 自动切换到 akshare ETF → 开放基金 |
| 所有数据源失败 | 网络问题/接口变更 | 检查网络连接，查看日志 |

### 数据库问题

| 问题 | 解决 |
|------|------|
| 字段找不到 | SQLite 不支持直接 DROP COLUMN，需要备份 → 重建表 |
| 数据库损坏 | 使用 `backend/data/backups/` 下的备份恢复 |
| 数据不一致 | 删除 `financial_analyzer.db` 文件后重启（会重新建表） |

### AI 分析问题

| 问题 | 解决 |
|------|------|
| 返回降级报告 | 检查 DeepSeek API Key 和网络连接 |
| JSON 解析失败 | 检查 AI prompt 中的 JSON 格式定义 |
| 建议不准确 | 调整 prompt 或修改 `INVESTMENT_STYLE` 配置 |
| 持有时长为 0 | 检查交易记录是否创建成功，确认 `tx_date` 字段是否正确 |
