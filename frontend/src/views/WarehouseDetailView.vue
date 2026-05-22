<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import type { WarehouseItem, AnalysisResult } from '@/types'
import FinancialChart from '@/components/FinancialChart.vue'

const route = useRoute()
const router = useRouter()
const code = ref('')
const assetType = ref('stock')
const records = ref<WarehouseItem[]>([])
const loading = ref(false)
const error = ref('')

// Detail modal
const showModal = ref(false)
const selectedRecord = ref<WarehouseItem | null>(null)
const parsedDetail = ref<AnalysisResult | null>(null)
const detailLoading = ref(false)

const showProfessional = ref(false)

async function load() {
  code.value = (route.params.code as string) || ''
  assetType.value = (route.query.type as string) || 'stock'
  if (!code.value) return
  loading.value = true
  error.value = ''
  try {
    records.value = await api.getWarehouseRecordsByCode(code.value, assetType.value)
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function openDetail(id: number) {
  detailLoading.value = true
  showModal.value = true
  selectedRecord.value = null
  parsedDetail.value = null
  showProfessional.value = false
  try {
    const item = await api.getWarehouseItem(id)
    selectedRecord.value = item
    try {
      const parsed = JSON.parse(item.detail_json)
      parsedDetail.value = parsed as AnalysisResult
    } catch {
      parsedDetail.value = null
    }
  } catch (e: any) {
    error.value = e.message || '加载详情失败'
  } finally {
    detailLoading.value = false
  }
}

function closeModal() {
  showModal.value = false
  selectedRecord.value = null
  parsedDetail.value = null
  showProfessional.value = false
}

async function removeItem(id: number) {
  if (!confirm('确认删除此分析记录？')) return
  try {
    await api.deleteWarehouseItem(id)
    records.value = records.value.filter(r => r.id !== id)
    if (selectedRecord.value?.id === id) closeModal()
  } catch (e: any) {
    error.value = e.message || '删除失败'
  }
}

function goBack() {
  router.push('/warehouse')
}

function timeStr(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

function typeLabel(t: string) {
  return t === 'fund' ? '基金' : '股票'
}

const chartData = computed(() => parsedDetail.value?.market_data || [])

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-sm btn-outline" @click="goBack">← 返回</button>
        <h1 class="page-title">{{ code }}</h1>
        <span v-if="records.length > 0" class="tag" :class="assetType === 'fund' ? 'tag-yellow' : 'tag-blue'">
          {{ typeLabel(assetType) }}
        </span>
        <span v-if="records.length > 0" class="record-count">{{ records.length }}条分析记录</span>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: var(--red); margin-bottom: 1rem;">
      <p class="text-red">{{ error }}</p>
    </div>

    <div v-if="loading" class="card text-center" style="padding:2rem;">
      <p class="text-secondary">加载中...</p>
    </div>

    <div v-if="!loading" class="list-panel">
      <div v-if="records.length === 0" class="card empty-state">
        <p class="text-secondary">暂无分析记录</p>
      </div>
      <div
        v-for="r in records"
        :key="r.id"
        class="record-item card"
        @click="openDetail(r.id)"
      >
        <div class="record-top">
          <span class="record-summary">{{ r.summary }}</span>
          <span class="record-time">{{ timeStr(r.created_at) }}</span>
          <button class="btn btn-danger btn-xs" @click.stop="removeItem(r.id)">删除</button>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal-container card">
          <div class="modal-header">
            <div v-if="selectedRecord" class="modal-title-area">
              <h2 class="modal-title">{{ selectedRecord.code }}</h2>
              <span v-if="parsedDetail?.name" class="full-name">{{ parsedDetail.name }}</span>
              <span class="modal-time">{{ timeStr(selectedRecord.created_at) }}</span>
            </div>
            <div class="modal-actions">
              <button v-if="selectedRecord" class="btn btn-danger btn-sm" @click="removeItem(selectedRecord.id)">删除</button>
              <button class="btn btn-sm" @click="closeModal">✕</button>
            </div>
          </div>

          <div v-if="detailLoading" class="modal-loading">
            <p class="text-secondary">加载详情...</p>
          </div>

          <div v-else-if="parsedDetail" class="modal-body">
            <!-- Professional Toggle -->
            <div class="toggle-bar">
              <button class="toggle-btn" :class="{ active: !showProfessional }" @click="showProfessional = false">通俗结论</button>
              <button class="toggle-btn" :class="{ active: showProfessional }" @click="showProfessional = true">专业分析</button>
            </div>

            <!-- Simple View -->
            <template v-if="!showProfessional">
              <div class="summary-section card-inner">
                <p class="summary-text">{{ parsedDetail.ai_report?.summary || selectedRecord?.summary || '暂无摘要' }}</p>
              </div>

              <div v-if="parsedDetail.ai_report?.personal_advice" class="detail-section card-inner card-advice">
                <h3 class="section-title">个人持仓专属建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.personal_advice }}</p>
              </div>

              <div v-if="parsedDetail.ai_report?.market_advice" class="detail-section card-inner card-info">
                <h3 class="section-title">通用市场参考建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.market_advice }}</p>
              </div>

              <div v-if="parsedDetail.ai_report?.position_action" class="action-bar">
                <span class="action-label">操作方向</span>
                <span class="action-chip" :class="{
                  'chip-hold': parsedDetail.ai_report.position_action.includes('持有'),
                  'chip-add': parsedDetail.ai_report.position_action.includes('加仓'),
                  'chip-reduce': parsedDetail.ai_report.position_action.includes('减仓') || parsedDetail.ai_report.position_action.includes('观望'),
                }">{{ parsedDetail.ai_report.position_action }}</span>
              </div>

              <div class="grid-2">
                <div v-if="parsedDetail.ai_report?.buy_zone" class="detail-section card-inner card-buy">
                  <h3 class="section-title">买入区间</h3>
                  <p class="section-body">{{ parsedDetail.ai_report.buy_zone }}</p>
                </div>
                <div v-if="parsedDetail.ai_report?.sell_zone" class="detail-section card-inner card-sell">
                  <h3 class="section-title">止盈/止损</h3>
                  <p class="section-body">{{ parsedDetail.ai_report.sell_zone }}</p>
                </div>
              </div>

              <div v-if="parsedDetail.ai_report?.advice" class="detail-section card-inner card-advice">
                <h3 class="section-title">综合建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.advice }}</p>
              </div>
            </template>

            <!-- Professional View -->
            <template v-if="showProfessional">
              <div v-if="chartData.length > 0" class="detail-section chart-section">
                <h3 class="section-title">K线走势</h3>
                <FinancialChart :data="chartData" :asset-type="selectedRecord?.asset_type === 'fund' ? 'fund' : 'stock'" :height="400" />
              </div>

              <div class="summary-section card-inner">
                <p class="summary-text">{{ parsedDetail.ai_report?.summary || selectedRecord?.summary || '暂无摘要' }}</p>
              </div>

              <div v-if="parsedDetail.ai_report?.personal_advice" class="detail-section card-inner card-advice">
                <h3 class="section-title">个人持仓专属建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.personal_advice }}</p>
              </div>
              <div v-if="parsedDetail.ai_report?.market_advice" class="detail-section card-inner card-info">
                <h3 class="section-title">通用市场参考建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.market_advice }}</p>
              </div>

              <div v-if="parsedDetail.ai_report?.position_action" class="action-bar">
                <span class="action-label">操作方向</span>
                <span class="action-chip" :class="{
                  'chip-hold': parsedDetail.ai_report.position_action.includes('持有'),
                  'chip-add': parsedDetail.ai_report.position_action.includes('加仓'),
                  'chip-reduce': parsedDetail.ai_report.position_action.includes('减仓') || parsedDetail.ai_report.position_action.includes('观望'),
                }">{{ parsedDetail.ai_report.position_action }}</span>
              </div>

              <div class="grid-2">
                <div v-if="parsedDetail.ai_report?.buy_zone" class="detail-section card-inner card-buy">
                  <h3 class="section-title">买入区间</h3>
                  <p class="section-body">{{ parsedDetail.ai_report.buy_zone }}</p>
                </div>
                <div v-if="parsedDetail.ai_report?.sell_zone" class="detail-section card-inner card-sell">
                  <h3 class="section-title">止盈/止损</h3>
                  <p class="section-body">{{ parsedDetail.ai_report.sell_zone }}</p>
                </div>
              </div>

              <div class="grid-2">
                <div class="detail-section card-inner">
                  <h3 class="section-title">{{ selectedRecord?.asset_type === 'fund' ? '净值走势' : '技术面' }}</h3>
                  <p class="section-body">{{ parsedDetail.ai_report?.technical_view || '暂无数据' }}</p>
                </div>
                <div class="detail-section card-inner">
                  <h3 class="section-title">{{ selectedRecord?.asset_type === 'fund' ? '基金档案' : '基本面' }}</h3>
                  <p class="section-body">{{ parsedDetail.ai_report?.fundamental_view || '暂无数据' }}</p>
                </div>
              </div>

              <div class="grid-2">
                <div class="detail-section card-inner">
                  <h3 class="section-title">市场情绪</h3>
                  <p class="section-body">{{ parsedDetail.ai_report?.sentiment_view || '暂无数据' }}</p>
                </div>
                <div class="detail-section card-inner">
                  <h3 class="section-title">潜在机会</h3>
                  <p class="section-body">{{ parsedDetail.ai_report?.opportunity || '暂无数据' }}</p>
                </div>
              </div>

              <div v-if="parsedDetail.ai_report?.strategy" class="detail-section card-inner card-advice">
                <h3 class="section-title">策略建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report.strategy }}</p>
              </div>

              <div class="detail-section card-inner card-warning">
                <h3 class="section-title">风险提示</h3>
                <p class="section-body">{{ parsedDetail.ai_report?.risk_warning || '暂无数据' }}</p>
              </div>

              <div class="detail-section card-inner card-advice">
                <h3 class="section-title">综合建议</h3>
                <p class="section-body advice-text">{{ parsedDetail.ai_report?.advice || '暂无数据' }}</p>
              </div>
            </template>
          </div>

          <div v-else-if="selectedRecord && !parsedDetail" class="modal-body">
            <div class="detail-section">
              <h3 class="section-title">摘要</h3>
              <p>{{ selectedRecord.summary }}</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { max-width: 960px; margin: 0 auto; padding: 1.5rem 1.25rem; min-height: 100vh; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.header-left { display: flex; align-items: center; gap: 0.85rem; flex-wrap: wrap; }
.page-title { font-size: 1.6rem; font-weight: 700; }
.record-count { font-size: 0.9rem; color: var(--text-secondary); }

.list-panel { display: flex; flex-direction: column; gap: 0.6rem; }
.record-item { padding: 1rem 1.2rem; cursor: pointer; transition: all 0.2s; background: linear-gradient(135deg, rgba(22, 26, 40, 0.9), rgba(26, 30, 48, 0.8)); }
.record-item:hover { border-color: var(--accent); }
.record-top { display: flex; align-items: center; gap: 0.85rem; }
.record-summary { font-size: 0.95rem; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.record-time { font-size: 0.85rem; color: var(--text-secondary); white-space: nowrap; }

.empty-state { text-align: center; padding: 3.5rem 2rem; }
.text-center { text-align: center; }
.text-secondary { color: var(--text-secondary); }

.btn-outline { background: transparent; border: 1px solid var(--border); }
.btn-outline:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm { padding: 0.4rem 0.8rem; font-size: 0.85rem; }
.btn-xs { padding: 0.3rem 0.55rem; font-size: 0.82rem; }
.btn-danger { background: transparent; color: var(--red); border: 1px solid rgba(248, 113, 113, 0.3); }
.btn-danger:hover { background: var(--red-dim); border-color: var(--red); }

.tag { font-size: 0.8rem; padding: 0.2rem 0.6rem; border-radius: 100px; font-weight: 500; }
.tag-blue { background: rgba(79, 195, 247, 0.12); color: var(--accent); }
.tag-yellow { background: rgba(251, 191, 36, 0.12); color: var(--orange); }

/* Toggle */
.toggle-bar { display: flex; background: rgba(15, 17, 23, 0.5); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 3px; }
.toggle-btn { flex: 1; padding: 0.5rem 0; border: none; border-radius: 6px; background: transparent; color: var(--text-secondary); font-size: 0.88rem; cursor: pointer; transition: all 0.2s; font-weight: 500; }
.toggle-btn.active { background: var(--accent-dim); color: var(--accent); font-weight: 600; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,0.7); backdrop-filter: blur(8px); display: flex; align-items: flex-start; justify-content: center; padding: 1.5rem 1rem; overflow-y: auto; }
.modal-container {
  width: 100%; max-width: 820px; margin-top: 1rem;
  padding: 1.5rem;
  background: rgba(22, 26, 40, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow-lg);
  max-height: calc(100vh - 3rem); overflow-y: auto;
}
.modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem; }
.modal-title-area { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.modal-title { font-size: 1.35rem; font-weight: 700; }
.full-name { font-size: 0.9rem; color: var(--text-secondary); }
.modal-time { font-size: 0.85rem; color: var(--text-secondary); }
.modal-actions { display: flex; gap: 0.5rem; align-items: center; }
.modal-loading { text-align: center; padding: 3rem; }
.modal-body { display: flex; flex-direction: column; gap: 1rem; }
.summary-section { border-left: 3px solid var(--accent); padding-left: 0.85rem; }
.summary-text { font-size: 1.05rem; line-height: 1.7; }
.chart-section { padding: 0; }
.card-inner { background: rgba(15, 17, 23, 0.4); border: 1px solid rgba(42, 46, 58, 0.3); border-radius: var(--radius-sm); padding: 0.9rem 1rem; }
.card-warning { border-left: 3px solid var(--orange); }
.card-advice { border-left: 3px solid var(--accent); }
.card-info { border-left: 3px solid var(--accent-dim); }
.card-buy { border-left: 3px solid var(--green); }
.card-sell { border-left: 3px solid var(--red); }
.section-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.4rem; }
.section-body { font-size: 0.92rem; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; }
.advice-text { color: var(--text); font-size: 0.95rem; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
@media (max-width: 640px) { .grid-2 { grid-template-columns: 1fr; } }

.action-bar { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; }
.action-label { font-size: 0.88rem; color: var(--text-secondary); font-weight: 500; }
.action-chip { display: inline-block; padding: 0.35rem 1rem; border-radius: 100px; font-size: 0.92rem; font-weight: 700; }
.chip-hold { background: rgba(79, 195, 247, 0.15); color: var(--accent); }
.chip-add { background: rgba(52, 211, 153, 0.15); color: var(--green); }
.chip-reduce { background: rgba(251, 191, 36, 0.15); color: var(--orange); }
</style>
