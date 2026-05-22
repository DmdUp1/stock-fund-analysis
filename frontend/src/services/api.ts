import type { AnalysisResult, PortfolioSummary, AutoTaskStatus, BackupInfo, WarehouseItem, WarehouseDetail, WarehouseGroup, TransactionItem } from '@/types'

// ── API Key 优先级: 运行时注入 > 编译时环境变量 ──
const RUNTIME_CONFIG = window.__RUNTIME_CONFIG__
const API_KEY = RUNTIME_CONFIG?.apiKey || import.meta.env.VITE_API_KEY || ''
const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(API_KEY ? { 'X-API-Key': API_KEY } : {}),
  }

  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  })

  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error')
    throw new Error(`${res.status}: ${text}`)
  }

  return res.json()
}

export const api = {
  // Analysis
  analyzeAsset(code: string, assetType = 'stock', name = '', start = '', end = '', costPrice = 0, shares = 0) {
    const params = new URLSearchParams({ asset_type: assetType, name })
    if (start) params.set('start', start)
    if (end) params.set('end', end)
    if (costPrice > 0) params.set('cost_price', String(costPrice))
    if (shares > 0) params.set('shares', String(shares))
    return request<AnalysisResult>(`/analysis/${code}?${params}`)
  },

  lookupName(code: string, assetType = 'stock') {
    return request<{ code: string; name: string }>(`/analysis/lookup/${code}?asset_type=${assetType}`)
  },

  // Portfolio
  getPortfolio() {
    return request<PortfolioSummary>('/portfolio')
  },

  addPosition(code: string, name: string, shares: number, costPrice: number, assetType = 'stock') {
    const params = new URLSearchParams({
      code, name,
      shares: String(shares),
      cost_price: String(costPrice),
      asset_type: assetType,
    })
    return request<{ status: string; message: string }>(`/portfolio/add?${params}`, { method: 'POST' })
  },

  removePosition(id: number) {
    return request<{ status: string; message: string }>(`/portfolio/${id}`, { method: 'DELETE' })
  },

  getPortfolioByCode(code: string, assetType = 'stock') {
    return request<{ id: number; code: string; name: string; asset_type: string; shares: number; cost_price: number; total_fees: number; added_at: string }>(
      `/portfolio/by-code/${code}?asset_type=${assetType}`
    )
  },

  updatePortfolioShares(itemId: number, shares: number, costPrice = 0) {
    const params = new URLSearchParams({ shares: String(shares) })
    if (costPrice > 0) params.set('cost_price', String(costPrice))
    return request<{ status: string; message: string }>(`/portfolio/${itemId}/shares?${params}`, { method: 'PUT' })
  },

  // Auto tasks
  getAutoStatus() {
    return request<AutoTaskStatus>('/auto/status')
  },

  getBackups() {
    return request<BackupInfo[]>('/auto/backups')
  },

  // Warehouse
  getWarehouse(assetType = '', limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (assetType) params.set('asset_type', assetType)
    return request<WarehouseItem[]>(`/warehouse?${params}`)
  },

  getWarehouseItem(id: number) {
    return request<WarehouseDetail>(`/warehouse/${id}`)
  },

  deleteWarehouseItem(id: number) {
    return request<{ status: string; message: string }>(`/warehouse/${id}`, { method: 'DELETE' })
  },

  getWarehouseLatest(code: string, assetType = 'stock') {
    return request<WarehouseDetail | null>(`/warehouse/by-code/${code}?asset_type=${assetType}`)
  },

  getWarehouseGroups(assetType = '') {
    const params = assetType ? `?asset_type=${assetType}` : ''
    return request<WarehouseGroup[]>(`/warehouse/groups${params}`)
  },

  getWarehouseRecordsByCode(code: string, assetType: string) {
    return request<WarehouseItem[]>(`/warehouse/by-code/${code}/all?asset_type=${assetType}`)
  },

  // Transactions
  addTransaction(data: {
    code: string; name?: string; asset_type: string; tx_type: string;
    shares: number; price: number; fee?: number; tx_date: string;
  }) {
    return request<TransactionItem>('/portfolio/transaction', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  getTransactions(portfolioId: number) {
    return request<TransactionItem[]>(`/portfolio/${portfolioId}/transactions`)
  },

  updateTransaction(txId: number, data: {
    tx_type: string; shares: number; price: number; fee?: number; tx_date: string;
  }) {
    return request<TransactionItem>(`/portfolio/transaction/${txId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteTransaction(txId: number) {
    return request<{ status: string; message: string }>(`/portfolio/transaction/${txId}`, { method: 'DELETE' })
  },
}
