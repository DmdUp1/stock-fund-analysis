export interface MarketDataItem {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  code: string
}

export interface AIReport {
  code: string
  name: string
  asset_type: string
  summary: string
  style: string
  technical_view: string
  fundamental_view: string
  sentiment_view: string
  risk_warning: string
  opportunity: string
  advice: string
  buy_zone: string
  sell_zone: string
  position_action: string
  strategy: string
  personal_advice: string
  market_advice: string
}

export interface AnalysisResult {
  code: string
  name: string
  asset_type: string
  ai_report: AIReport
  market_data: MarketDataItem[]
  generated_at: string
}

export interface PortfolioItem {
  id: number
  code: string
  name: string
  asset_type: string
  shares: number
  cost_price: number
  current_price: number
  market_value: number
  profit_loss: number
  profit_loss_pct: number
  holding_days: number
  daily_change_pct: number
  total_fees: number
  net_asset: number
  position_action?: string
  buy_zone?: string
  sell_zone?: string
  suggestion?: string
  suggestion_reason?: string
}

export interface AssetPortfolioSummary {
  items: PortfolioItem[]
  total_cost: number
  total_market_value: number
  total_profit_loss: number
  total_profit_loss_pct: number
}

export interface PortfolioSummary {
  stocks: AssetPortfolioSummary
  funds: AssetPortfolioSummary
  total_cost: number
  total_market_value: number
  total_profit_loss: number
  total_profit_loss_pct: number
}

export interface AutoTaskStatus {
  last_run: string | null
  next_run: string | null
  is_running: boolean
}

export interface BackupInfo {
  file_path: string
  file_size_bytes: number
  created_at: string
}

export interface WarehouseItem {
  id: number
  code: string
  asset_type: string
  summary: string
  created_at: string
}

export interface WarehouseDetail {
  id: number
  code: string
  asset_type: string
  summary: string
  detail_json: string
  created_at: string
}

export interface WarehouseGroup {
  code: string
  asset_type: string
  name: string
  latest_summary: string
  latest_time: string
  record_count: number
  portfolio_shares: number
  position_action: string
  buy_zone: string
  sell_zone: string
  suggestion: string
  suggestion_reason?: string
}

export interface TransactionItem {
  id: number
  portfolio_id: number | null
  code: string
  name: string
  asset_type: string
  tx_type: 'buy' | 'add' | 'reduce' | 'sell'
  shares: number
  price: number
  amount: number
  fee: number
  tx_date: string
  created_at: string
}
