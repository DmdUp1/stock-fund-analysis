<script setup lang="ts">
import { ref, watch } from 'vue'
import { api } from '@/services/api'
import type { AnalysisResult, AutoTaskStatus } from '@/types'
import AnalysisResultCard from '@/components/AnalysisResultCard.vue'
import FinancialChart from '@/components/FinancialChart.vue'

const code = ref('')
const name = ref('')
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)
const error = ref('')
const autoStatus = ref<AutoTaskStatus | null>(null)
const nameLoading = ref(false)

// Add to portfolio via transaction
const showAddDialog = ref(false)
const addTxType = ref('buy')
const addShares = ref(100)
const addCost = ref(10)
const addFee = ref(0)
const addDate = ref(new Date().toISOString().slice(0, 10))
const addLoading = ref(false)
const addError = ref('')
const addSuccess = ref('')

let lookupTimer: ReturnType<typeof setTimeout> | null = null

async function doAnalyze() {
  const trimmed = code.value.trim()
  if (!trimmed) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api.analyzeAsset(trimmed, 'stock', name.value)
  } catch (e: any) {
    error.value = e.message || '分析请求失败'
  } finally {
    loading.value = false
  }
}

async function doLookupName() {
  const trimmed = code.value.trim()
  if (!trimmed) return
  if (nameLoading.value) return
  nameLoading.value = true
  try {
    const res = await api.lookupName(trimmed, 'stock')
    if (res.name && !name.value) {
      name.value = res.name
    }
  } catch { /* ignore */ }
  finally { nameLoading.value = false }
}

function onCodeInput() {
  if (lookupTimer) clearTimeout(lookupTimer)
  lookupTimer = setTimeout(() => {
    nameLoading.value = true
    doLookupName()
  }, 600)
}

watch(code, () => {
  // name is cleared only when user types new code
  // auto-fill will happen via onCodeInput
})

async function fetchStatus() {
  try {
    autoStatus.value = await api.getAutoStatus()
  } catch { /* ignore */ }
}
fetchStatus()

function timeStr(iso: string | null | undefined) {
  if (!iso) return '暂无'
  return new Date(iso).toLocaleString('zh-CN')
}

function openAddDialog() {
  addTxType.value = 'buy'
  addShares.value = 100
  addCost.value = result.value?.market_data?.[result.value.market_data.length - 1]?.close || 10
  addFee.value = 0
  addDate.value = new Date().toISOString().slice(0, 10)
  addError.value = ''
  addSuccess.value = ''
  showAddDialog.value = true
}

async function confirmAdd() {
  if (!result.value || !addDate.value || addShares.value <= 0 || addCost.value <= 0) return
  addLoading.value = true
  addError.value = ''
  addSuccess.value = ''
  try {
    await api.addTransaction({
      code: result.value.code,
      name: result.value.name || name.value,
      asset_type: 'stock',
      tx_type: addTxType.value,
      shares: addShares.value,
      price: addCost.value,
      fee: addFee.value,
      tx_date: addDate.value,
    })
    addSuccess.value = `已成功加入持仓：${result.value.code} ${result.value.name || name.value}`
    setTimeout(() => { showAddDialog.value = false; addSuccess.value = '' }, 1500)
  } catch (e: any) {
    addError.value = e.message || '添加失败'
  } finally {
    addLoading.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">股票分析</h1>
      <div class="status-badge" v-if="autoStatus">
        <span class="status-dot" :class="{ online: !!autoStatus.last_run }"></span>
        上次自动分析: {{ timeStr(autoStatus.last_run) }}
      </div>
    </div>

    <div class="search-box card">
      <div class="search-row">
        <div class="input-group">
          <input
            v-model="code"
            type="text"
            placeholder="股票代码，如 000001"
            @keyup.enter="doAnalyze"
            @input="onCodeInput"
            class="code-input"
          />
          <input
            v-model="name"
            type="text"
            placeholder="名称（自动填充）"
            class="name-input"
          />
          <span v-if="nameLoading" class="input-spinner"></span>
        </div>
        <button class="btn btn-primary" :disabled="loading || !code.trim()" @click="doAnalyze">
          <span v-if="loading" class="spinner"></span>
          <span v-else>分析</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="card mt-4" style="border-color: var(--red);">
      <p class="text-red">{{ error }}</p>
    </div>

    <!-- Chart section -->
    <div v-if="result && result.market_data && result.market_data.length > 0" class="card mt-4 chart-section">
      <h3 class="section-title">{{ result.code }} {{ result.name }} - 历史行情走势</h3>
      <FinancialChart :data="result.market_data" asset-type="stock" :height="420" />
    </div>

    <AnalysisResultCard v-if="result" :result="result" :time-str="timeStr" />

    <!-- Add to portfolio -->
    <div v-if="result" class="card mt-4 action-bar">
      <button class="btn btn-primary" @click="openAddDialog">
        + 加入持仓
      </button>
    </div>

    <!-- Add dialog -->
    <Teleport to="body">
      <div v-if="showAddDialog" class="modal-overlay" @click.self="showAddDialog = false">
        <div class="modal card">
          <div class="modal-header">
            <h3>加入持仓</h3>
            <button class="btn btn-sm" @click="showAddDialog = false">✕</button>
          </div>
          <div class="modal-body">
            <p class="modal-desc" v-if="result">
              将 <strong>{{ result.code }}</strong>
              <span v-if="result.name || name"> ({{ result.name || name }})</span>
              加入股票持仓
            </p>
            <div class="form-grid">
              <div class="form-field">
                <label>交易类型</label>
                <select v-model="addTxType" class="form-input">
                  <option value="buy">买入建仓</option>
                  <option value="add">加仓</option>
                </select>
              </div>
              <div class="form-field">
                <label>份额确认日</label>
                <input v-model="addDate" type="date" class="form-input" />
              </div>
              <div class="form-field">
                <label>股数</label>
                <input v-model="addShares" type="number" step="any" min="0" class="form-input" />
              </div>
              <div class="form-field">
                <label>成交单价 (元)</label>
                <input v-model="addCost" type="number" step="0.0001" min="0" class="form-input" />
              </div>
              <div class="form-field">
                <label>手续费 (元)</label>
                <input v-model="addFee" type="number" step="0.01" min="0" class="form-input" placeholder="0" />
              </div>
            </div>
            <p v-if="addError" class="text-red text-sm mt-2">{{ addError }}</p>
            <p v-if="addSuccess" class="text-green text-sm mt-2">{{ addSuccess }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn" @click="showAddDialog = false">取消</button>
            <button class="btn btn-primary" :disabled="addLoading || !addShares || !addCost" @click="confirmAdd">
              {{ addLoading ? '添加中...' : '确认加入' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <div v-if="!result && !loading && !error" class="empty-state card">
      <p class="text-secondary">输入股票代码开始分析</p>
    </div>

    <!-- Global loading overlay -->
    <Teleport to="body">
      <div v-if="loading" class="global-loading">
        <div class="spinner"></div>
        <p class="loading-text">正在全维度分析，请稍候（约 10-30 秒）...</p>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { max-width: 960px; margin: 0 auto; padding: 1.5rem 1.25rem; min-height: 100vh; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem; }
.page-title { font-size: 1.6rem; font-weight: 700; }
.status-badge { display: flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; color: var(--text-secondary); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-secondary); flex-shrink: 0; }
.status-dot.online { background: var(--green); }

.search-box { padding: 1.25rem 1.5rem; }
.search-row { display: flex; gap: 0.75rem; align-items: center; }
.input-group { flex: 1; display: flex; gap: 0.5rem; align-items: center; position: relative; }
.code-input { flex: 0 0 150px; }
.name-input { flex: 1; min-width: 100px; }
.input-spinner { position: absolute; right: 0.5rem; width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .5s linear infinite; }

.spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(0,0,0,.2); border-top-color: #000; border-radius: 50%; animation: spin .6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.chart-section { padding: 1rem 1.25rem; }
.section-title { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.75rem; }

.action-bar { display: flex; gap: 0.75rem; justify-content: center; padding: 1rem; }

.empty-state { text-align: center; padding: 3.5rem 2rem; margin-top: 1.25rem; }
.mt-4 { margin-top: 1.25rem; }
.mt-2 { margin-top: 0.5rem; }

/* Add dialog modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.modal {
  width: 100%; max-width: 440px;
  padding: 1.5rem;
}
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.modal-header h3 { font-size: 1.15rem; font-weight: 600; }
.modal-desc { font-size: 0.92rem; color: var(--text-secondary); margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
.form-field { }
.form-field label { display: block; font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 0.3rem; }
.form-input { width: 100%; box-sizing: border-box; padding: 0.45rem 0.65rem; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text); font-size: 0.92rem; }
.form-select { width: 100%; }
.modal-footer { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--border); }
</style>
