<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/services/api'
import type { PortfolioSummary, PortfolioItem, AnalysisResult, TransactionItem } from '@/types'
import FinancialChart from '@/components/FinancialChart.vue'

const portfolio = ref<PortfolioSummary | null>(null)
const loading = ref(false)
const error = ref('')

// ── Transaction dialog (buy / add / reduce) ──
const showTxDialog = ref(false)
const txDialogMode = ref<'buy' | 'add' | 'reduce'>('buy')
const txDialogItem = ref<PortfolioItem | null>(null)
const dialogCode = ref('')
const dialogName = ref('')
const dialogDate = ref(new Date().toISOString().slice(0, 10))
const dialogShares = ref(1000)
const dialogPrice = ref(1)
const dialogFee = ref(0)
const dialogSubmitting = ref(false)
const dialogNameLoading = ref(false)
let lookupTimer: ReturnType<typeof setTimeout> | null = null

async function doLookupName() {
  const trimmed = dialogCode.value.trim()
  if (!trimmed) return
  dialogNameLoading.value = true
  try {
    const res = await api.lookupName(trimmed, 'fund')
    if (res.name && !dialogName.value) {
      dialogName.value = res.name
    }
  } catch { /* ignore */ }
  finally { dialogNameLoading.value = false }
}

function onCodeInput() {
  if (lookupTimer) clearTimeout(lookupTimer)
  dialogName.value = ''
  lookupTimer = setTimeout(doLookupName, 600)
}

function openTxDialog(mode: 'buy' | 'add' | 'reduce', item?: PortfolioItem) {
  txDialogMode.value = mode
  txDialogItem.value = item || null
  dialogDate.value = new Date().toISOString().slice(0, 10)
  dialogFee.value = 0
  dialogSubmitting.value = false

  if (mode === 'buy') {
    dialogCode.value = ''
    dialogName.value = ''
    dialogPrice.value = 1
    dialogShares.value = 1000
  } else if (item) {
    dialogCode.value = item.code
    dialogName.value = item.name
    dialogPrice.value = mode === 'add' ? item.current_price : item.cost_price
    dialogShares.value = mode === 'reduce' ? item.shares : 0
  }
  showTxDialog.value = true
}

function closeTxDialog() {
  showTxDialog.value = false
  txDialogItem.value = null
  dialogCode.value = ''
  dialogName.value = ''
}

async function submitTxDialog() {
  if (!dialogCode.value.trim() || !dialogDate.value || dialogShares.value <= 0 || dialogPrice.value <= 0) return
  dialogSubmitting.value = true
  try {
    await api.addTransaction({
      code: dialogCode.value.trim(),
      name: dialogName.value,
      asset_type: 'fund',
      tx_type: txDialogMode.value,
      shares: dialogShares.value,
      price: dialogPrice.value,
      fee: dialogFee.value,
      tx_date: dialogDate.value,
    })
    closeTxDialog()
    await load()
  } catch (e: any) {
    error.value = e.message || '提交交易失败'
  } finally {
    dialogSubmitting.value = false
  }
}

const items = computed<PortfolioItem[]>(() => {
  if (!portfolio.value) return []
  return portfolio.value.funds.items
})

const fundSummary = computed(() => {
  if (!portfolio.value) return null
  return portfolio.value.funds
})

const totalFees = computed(() => {
  if (!portfolio.value) return 0
  return portfolio.value.funds.items.reduce((s, i) => s + i.total_fees, 0)
})

const netAsset = computed(() => {
  if (!portfolio.value) return 0
  return portfolio.value.funds.total_market_value - totalFees.value
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    portfolio.value = await api.getPortfolio()
    // 预加载交易记录数量
    if (portfolio.value) {
      await Promise.all(portfolio.value.funds.items.map(item =>
        api.getTransactions(item.id).then(txs => {
          txCache.value[item.id] = txs
        }).catch(() => { })
      ))
    }
  } catch (e: any) {
    error.value = e.message || '获取持仓失败'
  } finally {
    loading.value = false
  }
}

// Analysis modal
const showModal = ref(false)
const modalLoading = ref(false)
const modalAnalysis = ref<AnalysisResult | null>(null)
const modalItem = ref<PortfolioItem | null>(null)
const showProfessional = ref(false)
const freshLoading = ref(false)

async function openAnalysis(item: PortfolioItem) {
  showModal.value = true
  modalLoading.value = true
  modalAnalysis.value = null
  modalItem.value = item
  showProfessional.value = false

  // 优先从分析仓库加载最近记录
  try {
    const cached = await api.getWarehouseLatest(item.code, 'fund')
    if (cached && cached.detail_json) {
      const parsed = JSON.parse(cached.detail_json) as AnalysisResult
      if (parsed && parsed.ai_report) {
        modalAnalysis.value = parsed
      }
    }
  } catch { /* ignore */ }

  // 仓库无记录则实时分析
  if (!modalAnalysis.value) {
    try {
      const result = await api.analyzeAsset(
        item.code, 'fund', item.name,
        '', '', item.cost_price, item.shares, item.holding_days,
      )
      modalAnalysis.value = result
    } catch (e: any) {
      error.value = e.message || '获取分析失败'
    }
  }

  modalLoading.value = false
}

async function refreshAnalysis() {
  if (!modalItem.value) return
  freshLoading.value = true
  try {
    const result = await api.analyzeAsset(
      modalItem.value.code, 'fund', modalItem.value.name,
      '', '', modalItem.value.cost_price, modalItem.value.shares, modalItem.value.holding_days,
    )
    modalAnalysis.value = result
  } catch (e: any) {
    error.value = e.message || '刷新分析失败'
  } finally {
    freshLoading.value = false
  }
}

function closeModal() {
  showModal.value = false
  modalAnalysis.value = null
  modalItem.value = null
  showProfessional.value = false
}

// ── Inline transaction panel per item ──
const expandedTx = ref<Record<number, boolean>>({})
const txCache = ref<Record<number, TransactionItem[]>>({})
const txLoading = ref<Record<number, boolean>>({})
const editingTxId = ref<number | null>(null)
const editTxForm = ref({ tx_type: 'add', shares: 0, price: 0, fee: 0, tx_date: '' })

function toggleTxPanel(itemId: number) {
  expandedTx.value[itemId] = !expandedTx.value[itemId]
  if (expandedTx.value[itemId] && !txCache.value[itemId]) {
    loadTxList(itemId)
  }
}

async function loadTxList(itemId: number) {
  txLoading.value[itemId] = true
  try {
    txCache.value[itemId] = await api.getTransactions(itemId)
  } catch { /* ignore */ }
  finally { txLoading.value[itemId] = false }
}

function startEditTx(tx: TransactionItem) {
  editingTxId.value = tx.id
  editTxForm.value = {
    tx_type: tx.tx_type,
    shares: tx.shares,
    price: tx.price,
    fee: tx.fee,
    tx_date: tx.tx_date,
  }
}

async function saveEditTx(tx: TransactionItem) {
  try {
    await api.updateTransaction(tx.id, editTxForm.value)
    editingTxId.value = null
    await loadTxList(tx.portfolio_id!)
    await load()
  } catch (e: any) {
    error.value = e.message || '修改交易失败'
  }
}

function cancelEdit() {
  editingTxId.value = null
}

async function deleteTx(txId: number, portfolioId: number) {
  if (!confirm('确认删除此交易记录？')) return
  try {
    await api.deleteTransaction(txId)
    await loadTxList(portfolioId)
    await load()
  } catch (e: any) {
    error.value = e.message || '删除交易失败'
  }
}

async function removePosition(id: number) {
  if (!confirm('确认删除此持仓？相关的交易记录也将被删除。')) return
  try {
    await api.removePosition(id)
    await load()
    if (modalItem.value?.id === id) closeModal()
  } catch (e: any) {
    error.value = e.message || '删除失败'
  }
}

// Inline add tx form
const showAddTxForm = ref<Record<number, boolean>>({})
const addTxForm = ref({ tx_type: 'add', shares: 0, price: 0, fee: 0, tx_date: '' })

function toggleAddTxForm(itemId: number) {
  showAddTxForm.value[itemId] = !showAddTxForm.value[itemId]
  if (showAddTxForm.value[itemId]) {
    addTxForm.value = { tx_type: 'add', shares: 0, price: 0, fee: 0, tx_date: new Date().toISOString().slice(0, 10) }
  }
}

async function submitAddTx(item: PortfolioItem) {
  if (addTxForm.value.shares <= 0 || addTxForm.value.price <= 0 || !addTxForm.value.tx_date) return
  try {
    await api.addTransaction({
      code: item.code,
      name: item.name,
      asset_type: 'fund',
      tx_type: 'add',
      shares: addTxForm.value.shares,
      price: addTxForm.value.price,
      fee: addTxForm.value.fee,
      tx_date: addTxForm.value.tx_date,
    })
    showAddTxForm.value[item.id] = false
    await loadTxList(item.id)
    await load()
  } catch (e: any) {
    error.value = e.message || '提交交易失败'
  }
}

const chartData = computed(() => modalAnalysis.value?.market_data || [])

function money(val: number) {
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
}

function pct(val: number) {
  return val.toFixed(4)
}

function suggestionClass(s: string): string {
  if (s.includes('加仓')) return 'sugo-add'
  if (s.includes('减仓')) return 'sugo-reduce'
  if (s.includes('清仓')) return 'sugo-sell'
  if (s.includes('定投')) return 'sugo-dca'
  return 'sugo-hold'
}

function zoneShort(zone: string): string {
  if (!zone) return ''
  const match = zone.match(/([\d.]+[～~–-][\d.]+)/)
  if (match && match[1]) return match[1]
  const parts = zone.split(/[。，,]/).filter(Boolean)
  return parts[0]?.replace(/^[：:]\s*/, '') || zone.slice(0, 25)
}

function txTypeLabel(t: string) {
  const map: Record<string, string> = { buy: '买入', add: '加仓', reduce: '减仓', sell: '卖出' }
  return map[t] || t
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">基金持仓</h1>
      <div class="header-actions">
        <button class="btn btn-primary" @click="openTxDialog('buy')">+ 买入建仓</button>
      </div>
    </div>

    <div v-if="error" class="card mt-4" style="border-color: var(--red);">
      <p class="text-red">{{ error }}</p>
    </div>

    <div v-if="loading && !portfolio" class="card mt-4 skeleton-card">
      <div class="skeleton-line w-60"></div>
      <div class="skeleton-line w-80"></div>
      <div class="skeleton-line w-40"></div>
    </div>

    <!-- Summary bar -->
    <div v-if="fundSummary && items.length > 0" class="summary-bar">
      <div class="summary-stat">
        <span class="stat-label">总成本</span>
        <span class="stat-val">¥{{ money(fundSummary.total_cost) }}</span>
      </div>
      <div class="summary-stat">
        <span class="stat-label">总市值</span>
        <span class="stat-val">¥{{ money(fundSummary.total_market_value) }}</span>
      </div>
      <div class="summary-stat">
        <span class="stat-label">盈亏</span>
        <span class="stat-val" :class="fundSummary.total_profit_loss >= 0 ? 'clr-up' : 'clr-down'">
          {{ fundSummary.total_profit_loss >= 0 ? '+' : '' }}{{ pct(fundSummary.total_profit_loss_pct) }}%
        </span>
      </div>
      <div class="summary-stat">
        <span class="stat-label">手续费</span>
        <span class="stat-val clr-secondary">¥{{ money(totalFees) }}</span>
      </div>
      <div class="summary-stat">
        <span class="stat-label">净资产</span>
        <span class="stat-val" :class="netAsset >= 0 ? 'clr-up' : 'clr-down'">¥{{ money(netAsset) }}</span>
      </div>
    </div>

    <!-- Position cards -->
    <div v-if="items.length > 0" class="position-list">
      <div v-for="item in items" :key="item.id" class="pos-card card">
        <div class="pos-header">
          <div class="pos-title">
            <span class="pos-code">{{ item.code }}</span>
            <span class="pos-name">{{ item.name }}</span>
            <span class="tag tag-yellow">基金</span>
          </div>
          <div class="pos-header-actions">
            <button class="btn btn-xs btn-outline" @click="openAnalysis(item)">分析</button>
            <button class="btn btn-xs btn-danger" @click="removePosition(item.id)">删除</button>
          </div>
        </div>

        <div class="pos-stats">
          <div class="ps-item">
            <span class="ps-label">份额</span>
            <span class="ps-value">{{ item.shares }}份</span>
          </div>
          <div class="ps-item">
            <span class="ps-label">成本净值</span>
            <span class="ps-value">¥{{ money(item.cost_price) }}</span>
          </div>
          <div class="ps-item">
            <span class="ps-label">现净值</span>
            <span class="ps-value">¥{{ money(item.current_price) }}</span>
          </div>
          <div class="ps-item">
            <span class="ps-label">市值</span>
            <span class="ps-value">¥{{ money(item.market_value) }}</span>
          </div>
          <div class="ps-item">
            <span class="ps-label">昨日</span>
            <span class="ps-value" :class="item.daily_change_pct >= 0 ? 'clr-up' : 'clr-down'">
              {{ item.daily_change_pct >= 0 ? '+' : '' }}{{ pct(item.daily_change_pct) }}%
            </span>
          </div>
          <div class="ps-item">
            <span class="ps-label">累计盈亏</span>
            <span class="ps-value" :class="item.profit_loss >= 0 ? 'clr-up' : 'clr-down'">
              {{ item.profit_loss >= 0 ? '+' : '' }}{{ pct(item.profit_loss_pct) }}%
              <span class="ps-amount">({{ item.profit_loss >= 0 ? '+' : '' }}¥{{ money(item.profit_loss) }})</span>
            </span>
          </div>
          <div class="ps-item">
            <span class="ps-label">持有</span>
            <span class="ps-value clr-secondary">{{ item.holding_days }}天</span>
          </div>
        </div>

        <div class="pos-actions">
          <button class="btn btn-xs btn-add" @click.stop="openTxDialog('add', item)">+ 加仓</button>
          <button class="btn btn-xs btn-reduce" @click.stop="openTxDialog('reduce', item)">- 减仓</button>
          <button class="btn btn-xs btn-outline" @click="toggleTxPanel(item.id)">
            {{ expandedTx[item.id] ? '▲ 收起交易' : '▼ 交易记录' }}({{ txCache[item.id]?.length || 0 }})
          </button>
        </div>

        <div v-if="item.suggestion" class="pos-suggestion" :class="suggestionClass(item.suggestion)">
          <span class="sug-badge" :class="suggestionClass(item.suggestion)">{{ item.suggestion }}</span>
          <span v-if="item.buy_zone" class="zone zone-buy">{{ zoneShort(item.buy_zone) }}</span>
          <span v-if="item.sell_zone" class="zone zone-sell">{{ zoneShort(item.sell_zone) }}</span>
          <span v-if="item.suggestion_reason" class="sug-reason">{{ item.suggestion_reason }}</span>
        </div>

        <!-- Expandable Transaction Panel -->
        <div v-if="expandedTx[item.id]" class="tx-section">
          <div class="tx-divider"></div>
          <div class="tx-header">
            <span class="tx-title">交易记录</span>
            <button class="btn btn-xs btn-primary" @click="toggleAddTxForm(item.id)">
              {{ showAddTxForm[item.id] ? '取消' : '+ 新增' }}
            </button>
          </div>

          <div v-if="showAddTxForm[item.id]" class="tx-add-form">
            <label class="tx-label">日期 <input v-model="addTxForm.tx_date" type="date" class="fi-xs" /></label>
            <label class="tx-label">份额 <input v-model="addTxForm.shares" type="number" step="0.0001" min="0"
                class="fi-xs" placeholder="份额" /></label>
            <label class="tx-label">净值 <input v-model="addTxForm.price" type="number" step="0.0001" min="0"
                class="fi-xs" placeholder="净值" /></label>
            <label class="tx-label">手续费 <input v-model="addTxForm.fee" type="number" step="0.01" min="0" class="fi-xs"
                placeholder="手续费" /></label>
            <button class="btn btn-primary btn-xs" @click="submitAddTx(item)">确认</button>
          </div>

          <div v-if="txLoading[item.id]" class="tx-status">加载中...</div>
          <div v-else-if="!txCache[item.id] || txCache[item.id]!.length === 0" class="tx-status clr-secondary">暂无交易记录
          </div>
          <div v-else class="tx-list">
            <div v-for="tx in txCache[item.id]!" :key="tx.id" class="tx-row">
              <template v-if="editingTxId === tx.id">
                <label class="tx-label">日期 <input v-model="editTxForm.tx_date" type="date" class="fi-xs" /></label>
                <label class="tx-label">份额 <input v-model="editTxForm.shares" type="number" step="0.0001" min="0"
                    class="fi-xs" /></label>
                <label class="tx-label">净值 <input v-model="editTxForm.price" type="number" step="0.0001" min="0"
                    class="fi-xs" /></label>
                <label class="tx-label">手续费 <input v-model="editTxForm.fee" type="number" step="0.01" min="0"
                    class="fi-xs" /></label>
                <button class="btn btn-primary btn-xs" @click="saveEditTx(tx)">保存</button>
                <button class="btn btn-xs" @click="cancelEdit">取消</button>
              </template>
              <template v-else>
                <span class="tx-date">{{ tx.tx_date }}</span>
                <span class="tx-type" :class="'txt-' + tx.tx_type">{{ txTypeLabel(tx.tx_type) }}</span>
                <span class="tx-shares">{{ tx.shares }}份</span>
                <span class="tx-price">净值 ¥<span style="color: gold;">{{ money(tx.price) }}</span></span>
                <span class="tx-fee">手续费 ¥<span style="color: gold;">{{ money(tx.fee) }}</span></span>
                <span class="tx-amount">总价值 ¥<span style="color: gold;">{{ money(tx.amount) }}</span></span>
                <div class="tx-act">
                  <button class="btn btn-xs btn-outline" @click="startEditTx(tx)">✎</button>
                  <button class="btn btn-xs btn-outline" @click="deleteTx(tx.id, item.id)">🗑</button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="items.length === 0 && !loading" class="card empty-state mt-4">
      <p class="clr-secondary">暂无基金持仓</p>
      <p class="text-sm mt-2 clr-secondary">点击上方"买入建仓"添加首笔交易</p>
    </div>

    <!-- ── Transaction Dialog (buy / add / reduce) ── -->
    <Teleport to="body">
      <div v-if="showTxDialog" class="modal-overlay" @click.self="closeTxDialog">
        <div class="modal-card card">
          <div class="modal-hd">
            <h3>{{ txDialogMode === 'buy' ? '买入建仓' : txDialogMode === 'add' ? '加仓' : '减仓' }}</h3>
            <button class="btn btn-sm" @click="closeTxDialog">✕</button>
          </div>
          <div class="modal-bd">
            <p v-if="txDialogMode !== 'buy' && txDialogItem" class="modal-desc">
              标的：<strong>{{ txDialogItem.code }}</strong> {{ txDialogItem.name }}
              <span v-if="txDialogMode === 'reduce'">（当前持仓 {{ txDialogItem.shares }} 份）</span>
            </p>
            <div class="dlg-form">
              <template v-if="txDialogMode === 'buy'">
                <div class="field">
                  <label>基金代码</label>
                  <input v-model="dialogCode" type="text" placeholder="如 110011" class="form-input"
                    @input="onCodeInput" />
                  <span v-if="dialogNameLoading" class="field-spinner"></span>
                </div>
                <div class="field">
                  <label>基金名称</label>
                  <input v-model="dialogName" type="text" placeholder="自动填充" class="form-input" />
                </div>
              </template>
              <div class="field">
                <label>份额确认日</label>
                <input v-model="dialogDate" type="date" class="form-input" />
              </div>
              <div class="field">
                <label>交易份额</label>
                <input v-model="dialogShares" type="number" step="0.0001" min="0" class="form-input"
                  :max="txDialogMode === 'reduce' && txDialogItem ? txDialogItem.shares : undefined" />
                <span v-if="txDialogMode === 'reduce' && txDialogItem" class="field-hint">最大 {{ txDialogItem.shares }}
                  份</span>
              </div>
              <div class="field">
                <label>单位净值</label>
                <input v-model="dialogPrice" type="number" step="0.0001" min="0" class="form-input" />
              </div>
              <div class="field">
                <label>手续费</label>
                <input v-model="dialogFee" type="number" step="0.01" min="0" class="form-input" placeholder="0" />
              </div>
            </div>
            <p v-if="error" class="text-red text-sm mt-2">{{ error }}</p>
          </div>
          <div class="modal-ft">
            <button class="btn" @click="closeTxDialog">取消</button>
            <button class="btn btn-primary"
              :disabled="dialogSubmitting || !dialogCode || dialogShares <= 0 || dialogPrice <= 0 || !dialogDate"
              @click="submitTxDialog">
              {{ dialogSubmitting ? '提交中...' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Analysis Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-card card" style="max-width: 820px;">
          <div class="modal-hd">
            <div class="modal-title-area">
              <h2 class="modal-title">{{ modalItem?.code }}</h2>
              <span class="tag tag-yellow">基金</span>
              <span class="full-name">{{ modalItem?.name }}</span>
              <span v-if="modalItem" class="modal-holding">持有 {{ modalItem.holding_days }}天</span>
            </div>
            <div class="modal-actions">
              <button v-if="modalAnalysis" class="btn btn-sm btn-outline" :disabled="freshLoading"
                @click="refreshAnalysis">
                <span v-if="freshLoading" class="btn-spinner"></span>
                <span v-else>⟳ 刷新行情</span>
              </button>
              <button class="btn btn-sm" @click="closeModal">✕</button>
            </div>
          </div>

          <div v-if="modalLoading" class="modal-loading">
            <div class="loading-pulse">
              <div class="pulse-ring"></div>
              <p class="loading-text">加载分析数据...</p>
            </div>
          </div>

          <div v-else-if="modalAnalysis" class="modal-bd">
            <div class="toggle-bar">
              <button class="toggle-btn" :class="{ active: !showProfessional }"
                @click="showProfessional = false">通俗结论</button>
              <button class="toggle-btn" :class="{ active: showProfessional }"
                @click="showProfessional = true">专业分析</button>
            </div>

            <template v-if="!showProfessional">
              <div class="summary-section card-inner">
                <p class="summary-text">{{ modalAnalysis.ai_report.summary || '暂无摘要' }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.personal_advice" class="card-inner card-advice">
                <h3 class="sect-title">个人持仓专属建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.personal_advice }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.market_advice" class="card-inner card-info">
                <h3 class="sect-title">通用市场参考建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.market_advice }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.position_action" class="action-bar">
                <span class="action-label">操作方向</span>
                <span class="action-chip" :class="{
                  'chip-hold': modalAnalysis.ai_report.position_action.includes('持有'),
                  'chip-add': modalAnalysis.ai_report.position_action.includes('加仓'),
                  'chip-reduce': modalAnalysis.ai_report.position_action.includes('减仓') || modalAnalysis.ai_report.position_action.includes('观望'),
                }">{{ modalAnalysis.ai_report.position_action }}</span>
              </div>
              <div class="grid-2">
                <div v-if="modalAnalysis.ai_report.buy_zone" class="card-inner card-buy">
                  <h3 class="sect-title">买入区间</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.buy_zone }}</p>
                </div>
                <div v-if="modalAnalysis.ai_report.sell_zone" class="card-inner card-sell">
                  <h3 class="sect-title">止盈/止损</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.sell_zone }}</p>
                </div>
              </div>
              <div v-if="modalAnalysis.ai_report.advice" class="card-inner card-advice">
                <h3 class="sect-title">综合建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.advice }}</p>
              </div>
            </template>

            <template v-if="showProfessional">
              <div v-if="chartData.length > 0" class="chart-section">
                <h3 class="sect-title">净值走势</h3>
                <FinancialChart :data="chartData" asset-type="fund" :height="400" />
              </div>
              <div class="summary-section card-inner">
                <p class="summary-text">{{ modalAnalysis.ai_report.summary || '暂无摘要' }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.personal_advice" class="card-inner card-advice">
                <h3 class="sect-title">个人持仓专属建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.personal_advice }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.market_advice" class="card-inner card-info">
                <h3 class="sect-title">通用市场参考建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.market_advice }}</p>
              </div>
              <div v-if="modalAnalysis.ai_report.position_action" class="action-bar"><span
                  class="action-label">操作方向</span><span class="action-chip"
                  :class="{ 'chip-hold': modalAnalysis.ai_report.position_action.includes('持有'), 'chip-add': modalAnalysis.ai_report.position_action.includes('加仓'), 'chip-reduce': modalAnalysis.ai_report.position_action.includes('减仓') || modalAnalysis.ai_report.position_action.includes('观望') }">{{
                    modalAnalysis.ai_report.position_action }}</span></div>
              <div class="grid-2">
                <div v-if="modalAnalysis.ai_report.buy_zone" class="card-inner card-buy">
                  <h3 class="sect-title">买入区间</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.buy_zone }}</p>
                </div>
                <div v-if="modalAnalysis.ai_report.sell_zone" class="card-inner card-sell">
                  <h3 class="sect-title">止盈/止损</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.sell_zone }}</p>
                </div>
              </div>
              <div class="grid-2">
                <div class="card-inner">
                  <h3 class="sect-title">净值走势</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.technical_view || '暂无数据' }}</p>
                </div>
                <div class="card-inner">
                  <h3 class="sect-title">基金档案</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.fundamental_view || '暂无数据' }}</p>
                </div>
              </div>
              <div class="grid-2">
                <div class="card-inner">
                  <h3 class="sect-title">市场情绪</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.sentiment_view || '暂无数据' }}</p>
                </div>
                <div class="card-inner">
                  <h3 class="sect-title">潜在机会</h3>
                  <p class="sect-body">{{ modalAnalysis.ai_report.opportunity || '暂无数据' }}</p>
                </div>
              </div>
              <div v-if="modalAnalysis.ai_report.strategy" class="card-inner card-advice">
                <h3 class="sect-title">策略建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.strategy }}</p>
              </div>
              <div class="card-inner card-warning">
                <h3 class="sect-title">风险提示</h3>
                <p class="sect-body">{{ modalAnalysis.ai_report.risk_warning || '暂无数据' }}</p>
              </div>
              <div class="card-inner card-advice">
                <h3 class="sect-title">综合建议</h3>
                <p class="sect-body advice-text">{{ modalAnalysis.ai_report.advice || '暂无数据' }}</p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page {
  max-width: 1040px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
  min-height: 100vh;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.page-title {
  font-size: 1.7rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.mt-4 {
  margin-top: 1rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.text-sm {
  font-size: 0.85rem;
}

.clr-secondary {
  color: var(--text-secondary);
}

.clr-up {
  color: var(--green);
}

.clr-down {
  color: var(--red);
}

/* Summary bar */
.summary-bar {
  display: flex;
  gap: 0.75rem;
  background: linear-gradient(135deg, rgba(22, 26, 40, 0.9), rgba(26, 30, 48, 0.85));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
  backdrop-filter: blur(12px);
}

.summary-stat {
  text-align: center;
  padding: 0 1rem;
  position: relative;
}

.summary-stat+.summary-stat::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10%;
  height: 80%;
  width: 1px;
  background: linear-gradient(to bottom, transparent, var(--border), transparent);
}

.stat-label {
  display: block;
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-val {
  font-size: 1.25rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* Position cards */
.position-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.pos-card {
  padding: 1.25rem 1.35rem;
  background: linear-gradient(135deg, rgba(22, 26, 40, 0.9), rgba(26, 30, 48, 0.8));
  border: 1px solid var(--border);
  position: relative;
  overflow: hidden;
}

.pos-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(79, 195, 247, 0.15), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.pos-card:hover::before {
  opacity: 1;
}

.pos-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.pos-title {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.pos-code {
  font-weight: 700;
  font-size: 1.15rem;
  font-variant-numeric: tabular-nums;
}

.pos-name {
  font-size: 0.92rem;
  color: var(--text-secondary);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pos-header-actions {
  display: flex;
  gap: 0.35rem;
}

/* Stats grid - Bento style */
.pos-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

@media (max-width: 600px) {
  .pos-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

.ps-item {
  text-align: center;
  padding: 0.5rem 0.3rem;
  background: rgba(15, 17, 23, 0.4);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(42, 46, 58, 0.3);
  transition: border-color 0.2s, background 0.2s;
}

.ps-item:hover {
  border-color: var(--border-hover);
  background: rgba(15, 17, 23, 0.6);
}

.ps-label {
  display: block;
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 0.2rem;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.ps-value {
  font-size: 1.08rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.ps-amount {
  font-size: 0.78rem;
  font-weight: 500;
  opacity: 0.8;
  display: inline-block;
  margin-left: 0.15rem;
}

/* Action buttons */
.pos-actions {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

/* Suggestion */
.pos-suggestion {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  margin-bottom: 0.3rem;
  border-left: 3px solid transparent;
}

.sug-badge {
  font-weight: 700;
  font-size: 0.85rem;
  padding: 0.15rem 0.55rem;
  border-radius: 100px;
}

.zone {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 100px;
  font-weight: 500;
}

.zone-buy {
  background: var(--green-dim);
  color: var(--green);
}

.zone-sell {
  background: var(--red-dim);
  color: var(--red);
}

.sug-reason {
  font-size: 0.78rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sugo-add .sug-badge {
  background: var(--green-dim);
  color: var(--green);
}

.sugo-add {
  background: rgba(52, 211, 153, 0.04);
  border-left-color: var(--green);
}

.sugo-reduce .sug-badge {
  background: var(--orange-dim);
  color: var(--orange);
}

.sugo-reduce {
  background: rgba(251, 191, 36, 0.04);
  border-left-color: var(--orange);
}

.sugo-sell .sug-badge {
  background: var(--red-dim);
  color: var(--red);
}

.sugo-sell {
  background: rgba(239, 68, 68, 0.04);
  border-left-color: #ef4444;
}

.sugo-dca .sug-badge {
  background: var(--accent-dim);
  color: var(--accent);
}

.sugo-dca {
  background: rgba(79, 195, 247, 0.04);
  border-left-color: var(--accent);
}

.sugo-hold .sug-badge {
  background: rgba(154, 160, 166, 0.1);
  color: var(--text-secondary);
}

.sugo-hold {
  background: rgba(154, 160, 166, 0.03);
  border-left-color: var(--text-secondary);
}

/* Transaction section */
.tx-section {
  margin-top: 0.35rem;
}

.tx-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
  margin-bottom: 0.6rem;
}

.tx-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.tx-title {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.tx-add-form {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 0.6rem 0.75rem;
  background: rgba(15, 17, 23, 0.5);
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 0.6rem;
}

.tx-status {
  text-align: center;
  padding: 0.6rem;
  font-size: 0.82rem;
}

.tx-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.tx-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  background: rgba(15, 17, 23, 0.3);
  border: 1px solid rgba(42, 46, 58, 0.2);
  border-radius: var(--radius-xs);
  font-size: 0.85rem;
  flex-wrap: wrap;
  transition: border-color 0.2s, background 0.2s;
}

.tx-row:hover {
  border-color: rgba(42, 46, 58, 0.5);
  background: rgba(15, 17, 23, 0.5);
}

.tx-date {
  color: var(--text-secondary);
  min-width: 80px;
  font-size: 0.82rem;
}

.tx-type {
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.txt-buy {
  background: var(--green-dim);
  color: var(--green);
}

.txt-add {
  background: var(--accent-dim);
  color: var(--accent);
}

.txt-reduce {
  background: var(--orange-dim);
  color: var(--orange);
}

.txt-sell {
  background: var(--red-dim);
  color: var(--red);
}

.tx-shares {
  min-width: 60px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.tx-price {
  color: var(--text-secondary);
}

.tx-fee {
  color: var(--text-secondary);
}

.tx-amount {
  font-weight: 600;
  min-width: 85px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.tx-act {
  display: flex;
  gap: 0.2rem;
  margin-left: auto;
}

/* Skeleton */
.skeleton-card {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.skeleton-line {
  height: 14px;
  border-radius: 8px;
  background: linear-gradient(90deg, rgba(42, 46, 58, 0.4) 25%, rgba(35, 39, 56, 0.6) 50%, rgba(42, 46, 58, 0.4) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.w-60 {
  width: 60%;
}

.w-80 {
  width: 80%;
}

.w-40 {
  width: 40%;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }

  100% {
    background-position: -200% 0;
  }
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1.5rem 1rem;
  overflow-y: auto;
}

.modal-card {
  width: 100%;
  max-width: 500px;
  margin-top: 1rem;
  padding: 1.5rem;
  background: rgba(22, 26, 40, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  max-height: calc(100vh - 3rem);
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.85rem;
}

.modal-hd h3 {
  font-size: 1.15rem;
  font-weight: 600;
}

.modal-bd {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal-ft {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--border);
}

.modal-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.modal-title-area {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
}

.modal-actions {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}

.modal-loading {
  text-align: center;
  padding: 3rem;
}

.loading-pulse {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.pulse-ring {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(42, 46, 58, 0.4);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .7s linear infinite;
  box-shadow: 0 0 20px rgba(79, 195, 247, 0.08);
}

.loading-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Analysis modal needs wider max-width */
.modal-card[style*="820px"] {
  max-width: 820px;
}

/* Dialog form */
.dlg-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  position: relative;
}

.field label {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.field-hint {
  font-size: 0.75rem;
  color: var(--orange);
}

.form-input {
  width: 100%;
  padding: 0.55rem 0.8rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(15, 17, 23, 0.6);
  color: var(--text);
  font-size: 0.95rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.08);
}

/* Buttons */
.btn-xs {
  padding: 0.3rem 0.6rem;
  font-size: 0.82rem;
}

.btn-sm {
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
}

.btn-primary {
  background: linear-gradient(135deg, var(--accent) 0%, #29b6f6 100%);
  color: #000;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
  box-shadow: 0 0 20px rgba(79, 195, 247, 0.2);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
}

.btn-outline:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.btn-danger {
  color: var(--red);
}

.btn-danger:hover {
  background: var(--red-dim);
  border-color: var(--red);
}

.btn-add {
  color: var(--green);
  border-color: rgba(52, 211, 153, 0.3);
}

.btn-add:hover {
  background: var(--green-dim);
  border-color: var(--green);
}

.btn-reduce {
  color: var(--orange);
  border-color: rgba(251, 191, 36, 0.3);
}

.btn-reduce:hover {
  background: var(--orange-dim);
  border-color: var(--orange);
}

.empty-state {
  text-align: center;
  padding: 3rem 1.5rem;
}

/* FI small input */
.fi-xs {
  width: 120px;
  padding: 0.3rem 0.4rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-xs);
  background: rgba(15, 17, 23, 0.6);
  color: var(--text);
  font-size: 0.82rem;
  transition: border-color 0.2s;
}

.fi-xs:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(79, 195, 247, 0.06);
}

/* Toggle bar (analysis modal) */
.toggle-bar {
  display: flex;
  background: rgba(15, 17, 23, 0.5);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 3px;
}

.toggle-btn {
  flex: 1;
  padding: 0.45rem 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.toggle-btn.active {
  background: var(--accent-dim);
  color: var(--accent);
  font-weight: 600;
}

.card-inner {
  background: rgba(15, 17, 23, 0.4);
  border: 1px solid rgba(42, 46, 58, 0.3);
  border-radius: var(--radius-sm);
  padding: 0.8rem 0.9rem;
}

.card-advice {
  border-left: 3px solid var(--accent);
}

.card-info {
  border-left: 3px solid var(--accent-dim);
}

.card-buy {
  border-left: 3px solid var(--green);
}

.card-sell {
  border-left: 3px solid var(--red);
}

.card-warning {
  border-left: 3px solid var(--orange);
}

.sect-title {
  font-size: 0.92rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
  color: var(--text);
}

.sect-body {
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.advice-text {
  color: var(--text);
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}

@media (max-width: 640px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}

.summary-section {
  border-left: 3px solid var(--accent);
  padding-left: 0.75rem;
}

.summary-text {
  font-size: 1rem;
  line-height: 1.6;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0;
}

.action-label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.action-chip {
  display: inline-block;
  padding: 0.25rem 0.9rem;
  border-radius: 100px;
  font-size: 0.85rem;
  font-weight: 700;
}

.chip-hold {
  background: var(--accent-dim);
  color: var(--accent);
}

.chip-add {
  background: var(--green-dim);
  color: var(--green);
}

.chip-reduce {
  background: var(--orange-dim);
  color: var(--orange);
}

.chart-section {
  padding: 0;
}

.tag {
  font-size: 0.78rem;
  padding: 0.15rem 0.5rem;
  border-radius: 100px;
  font-weight: 500;
}

.tag-blue {
  background: var(--accent-dim);
  color: var(--accent);
}

.tag-yellow {
  background: rgba(251, 191, 36, 0.12);
  color: var(--orange);
}

.full-name {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.modal-holding { font-size: 0.82rem; color: var(--text-secondary); background: rgba(15, 17, 23, 0.4); padding: 0.15rem 0.55rem; border-radius: 100px; font-weight: 500; white-space: nowrap; }

.text-red {
  color: var(--red);
}

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(42, 46, 58, 0.4);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .5s linear infinite;
}

.field-spinner {
  position: absolute;
  right: 0.6rem;
  top: 2.2rem;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(42, 46, 58, 0.4);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .5s linear infinite;
}

.tx-label {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.82rem;
  color: var(--text-secondary);
  white-space: nowrap;
}
</style>
