<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import type { WarehouseGroup, PortfolioSummary, PortfolioItem } from '@/types'

const router = useRouter()
const groups = ref<WarehouseGroup[]>([])
const loading = ref(false)
const error = ref('')
const filterType = ref<'all' | 'stock' | 'fund'>('all')
const portfolioMap = ref<Record<string, PortfolioItem>>({})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [g, p] = await Promise.all([
      api.getWarehouseGroups(filterType.value === 'all' ? '' : filterType.value),
      api.getPortfolio().catch(() => null),
    ])
    groups.value = g

    // Build portfolio lookup map by code
    const map: Record<string, PortfolioItem> = {}
    if (p) {
      const allItems = [...(p.stocks?.items || []), ...(p.funds?.items || [])]
      for (const item of allItems) {
        map[item.code] = item
      }
    }
    portfolioMap.value = map
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function portfolioFor(g: WarehouseGroup): PortfolioItem | null {
  return portfolioMap.value[g.code] || null
}

function openDetail(code: string, assetType: string) {
  router.push(`/warehouse/${code}?type=${assetType}`)
}

function typeLabel(t: string) {
  return t === 'fund' ? '基金' : '股票'
}

function timeStr(iso: string) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">分析仓库</h1>
      <div class="filter-group">
        <button class="filter-btn" :class="{ active: filterType === 'all' }" @click="filterType = 'all'; load()">全部</button>
        <button class="filter-btn" :class="{ active: filterType === 'stock' }" @click="filterType = 'stock'; load()">股票</button>
        <button class="filter-btn" :class="{ active: filterType === 'fund' }" @click="filterType = 'fund'; load()">基金</button>
      </div>
    </div>

    <div v-if="error" class="card" style="border-color: var(--red); margin-bottom: 1rem;">
      <p class="text-red">{{ error }}</p>
    </div>

    <div v-if="loading" class="card text-center" style="padding:2rem;">
      <p class="text-secondary">加载中...</p>
    </div>

    <div v-if="!loading" class="group-list">
      <div v-if="groups.length === 0" class="card empty-state">
        <p class="text-secondary">暂无分析记录</p>
        <p class="text-sm mt-2 text-secondary">前往股票分析或基金分析页面开始分析</p>
      </div>
      <div
        v-for="g in groups"
        :key="g.code + '-' + g.asset_type"
        class="group-card card"
        @click="openDetail(g.code, g.asset_type)"
      >
        <div class="group-top">
          <span class="group-code">{{ g.code }}</span>
          <span v-if="g.name" class="group-name">{{ g.name }}</span>
          <span class="tag" :class="g.asset_type === 'fund' ? 'tag-yellow' : 'tag-blue'">
            {{ typeLabel(g.asset_type) }}
          </span>
          <span class="group-count">{{ g.record_count }}条记录</span>
          <span class="group-time">{{ timeStr(g.latest_time) }}</span>
        </div>
        <div v-if="g.portfolio_shares > 0" class="group-portfolio-info">
          <span class="pi-item">持仓 {{ g.portfolio_shares }}{{ g.asset_type === 'fund' ? '份' : '股' }}</span>
          <span v-if="portfolioFor(g)" class="pi-item" :class="(portfolioFor(g)!.daily_change_pct || 0) >= 0 ? 'text-red' : 'text-green'">
            昨 {{ (portfolioFor(g)!.daily_change_pct || 0) >= 0 ? '+' : '' }}{{ (portfolioFor(g)!.daily_change_pct || 0).toFixed(4) }}%
          </span>
          <span v-if="portfolioFor(g)" class="pi-item" :class="(portfolioFor(g)!.profit_loss_pct || 0) >= 0 ? 'text-red' : 'text-green'">
            累计 {{ (portfolioFor(g)!.profit_loss_pct || 0) >= 0 ? '+' : '' }}{{ (portfolioFor(g)!.profit_loss_pct || 0).toFixed(4) }}%
          </span>
          <span v-if="portfolioFor(g)" class="pi-item text-secondary">
            市值 ¥{{ (portfolioFor(g)!.market_value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) }}
          </span>
        </div>
        <div class="group-summary">{{ g.latest_summary }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1040px; margin: 0 auto; padding: 1.5rem 1.25rem; min-height: 100vh; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.75rem; }
.page-title { font-size: 1.7rem; font-weight: 700; background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

.filter-group { display: flex; gap: 0.25rem; background: rgba(15, 17, 23, 0.5); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 3px; }
.filter-btn { padding: 0.5rem 1.1rem; border: none; border-radius: 6px; background: transparent; color: var(--text-secondary); cursor: pointer; font-size: 0.92rem; transition: all 0.15s; }
.filter-btn.active { background: var(--accent-dim); color: var(--accent); font-weight: 600; }
.filter-btn:hover:not(.active) { color: var(--text); }

.group-list { display: flex; flex-direction: column; gap: 0.85rem; }

.group-card {
  padding: 1.35rem 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  background: linear-gradient(135deg, rgba(22, 26, 40, 0.9), rgba(26, 30, 48, 0.8));
  position: relative;
  overflow: hidden;
}
.group-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(79, 195, 247, 0.15), transparent);
  opacity: 0; transition: opacity 0.3s;
}
.group-card:hover::before { opacity: 1; }
.group-card:hover { border-color: var(--accent); }

.group-top { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.6rem; }
.group-code { font-weight: 700; font-size: 1.15rem; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.group-name { font-size: 0.92rem; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.group-count { font-size: 0.85rem; color: var(--text-secondary); margin-left: 0.25rem; }
.group-time { font-size: 0.85rem; color: var(--text-secondary); margin-left: auto; white-space: nowrap; }
.group-summary {
  font-size: 0.92rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 0.4rem;
  line-height: 1.5;
}
.group-portfolio-info {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(15, 17, 23, 0.3);
  border-radius: var(--radius-xs);
  font-size: 0.88rem;
}
.pi-item { font-variant-numeric: tabular-nums; }

.text-center { text-align: center; }
.text-sm { font-size: 0.88rem; }
.mt-2 { margin-top: 0.5rem; }
.text-secondary { color: var(--text-secondary); }
.empty-state { text-align: center; padding: 3.5rem 2rem; }

.tag { font-size: 0.82rem; padding: 0.2rem 0.6rem; border-radius: 100px; font-weight: 500; }
.tag-blue { background: rgba(79, 195, 247, 0.12); color: var(--accent); }
.tag-yellow { background: rgba(251, 191, 36, 0.12); color: var(--orange); }
</style>
