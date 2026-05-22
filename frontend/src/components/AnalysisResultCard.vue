<script setup lang="ts">
import type { AnalysisResult } from '@/types'

defineProps<{
  result: AnalysisResult
  timeStr: (iso: string | null | undefined) => string
}>()

function typeLabel(t: string) {
  return t === 'fund' ? '基金' : '股票'
}
</script>

<template>
  <div class="result-area">
    <!-- Header -->
    <div class="card summary-card">
      <div class="summary-top">
        <div>
          <span class="stock-code">{{ result.code }}</span>
          <span class="stock-name" v-if="result.name">{{ result.name }}</span>
          <span class="type-tag tag" :class="result.asset_type === 'fund' ? 'tag-yellow' : 'tag-blue'">
            {{ typeLabel(result.asset_type) }}
          </span>
        </div>
        <span class="tag tag-blue">{{ result.ai_report.style }}</span>
      </div>
      <p class="summary-text">{{ result.ai_report.summary }}</p>
      <p class="text-secondary text-sm mt-2">分析时间: {{ timeStr(result.generated_at) }}</p>
    </div>

    <!-- Position Action chip -->
    <div v-if="result.ai_report.position_action" class="card action-bar-card">
      <span class="action-label">操作建议</span>
      <span
        class="action-chip"
        :class="{
          'chip-hold': result.ai_report.position_action.includes('持有'),
          'chip-add': result.ai_report.position_action.includes('加仓'),
          'chip-reduce': result.ai_report.position_action.includes('减仓') || result.ai_report.position_action.includes('观望'),
        }"
      >{{ result.ai_report.position_action }}</span>
    </div>

    <!-- Buy / Sell zone -->
    <div class="grid-2">
      <div v-if="result.ai_report.buy_zone" class="card buy-card">
        <h3 class="section-title">适宜买入区间</h3>
        <p class="section-body">{{ result.ai_report.buy_zone }}</p>
      </div>
      <div v-if="result.ai_report.sell_zone" class="card sell-card">
        <h3 class="section-title">止盈 / 止损</h3>
        <p class="section-body">{{ result.ai_report.sell_zone }}</p>
      </div>
    </div>

    <!-- Grid: Technical + Fundamental -->
    <div class="grid-2">
      <div class="card">
        <h3 class="section-title">{{ result.asset_type === 'fund' ? '净值走势' : '技术面' }}</h3>
        <p class="section-body">{{ result.ai_report.technical_view }}</p>
      </div>
      <div class="card">
        <h3 class="section-title">{{ result.asset_type === 'fund' ? '基金档案' : '基本面' }}</h3>
        <p class="section-body">{{ result.ai_report.fundamental_view }}</p>
      </div>
    </div>

    <!-- Grid: Sentiment + Opportunity -->
    <div class="grid-2">
      <div class="card">
        <h3 class="section-title">市场情绪</h3>
        <p class="section-body">{{ result.ai_report.sentiment_view }}</p>
      </div>
      <div class="card">
        <h3 class="section-title">潜在机会</h3>
        <p class="section-body">{{ result.ai_report.opportunity }}</p>
      </div>
    </div>

    <!-- Strategy -->
    <div v-if="result.ai_report.strategy" class="card advice-card">
      <h3 class="section-title">策略建议</h3>
      <p class="section-body advice-text">{{ result.ai_report.strategy }}</p>
    </div>

    <!-- Risk Warning -->
    <div class="card warning-card">
      <h3 class="section-title">风险提示</h3>
      <p class="section-body">{{ result.ai_report.risk_warning }}</p>
    </div>

    <!-- Full Advice -->
    <div class="card advice-card">
      <h3 class="section-title">综合建议</h3>
      <p class="section-body advice-text">{{ result.ai_report.advice }}</p>
    </div>
  </div>
</template>

<style scoped>
.result-area { display: flex; flex-direction: column; gap: 0.75rem; margin-top: 1rem; }
.summary-card { border-left: 3px solid var(--accent); }
.summary-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; }
.stock-code { font-size: 1.25rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.stock-name { margin-left: 0.5rem; color: var(--text-secondary); font-size: 0.95rem; }
.type-tag { margin-left: 0.5rem; font-size: 0.75rem; }
.summary-text { font-size: 1.05rem; line-height: 1.7; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
@media (max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }

.section-title { font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; }
.section-body { font-size: 0.9rem; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; }
.advice-text { color: var(--text); font-size: 0.95rem; }

.buy-card { border-left: 3px solid var(--green); }
.sell-card { border-left: 3px solid var(--red); }
.warning-card { border-left: 3px solid var(--orange); }
.advice-card { border-left: 3px solid var(--accent); }

.action-bar-card { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.25rem; }
.action-label { font-size: 0.85rem; color: var(--text-secondary); font-weight: 500; }
.action-chip {
  display: inline-block;
  padding: 0.3rem 1rem;
  border-radius: 100px;
  font-size: 0.9rem;
  font-weight: 700;
}
.chip-hold { background: rgba(79, 195, 247, 0.15); color: var(--accent); }
.chip-add { background: rgba(52, 211, 153, 0.15); color: var(--green); }
.chip-reduce { background: rgba(251, 191, 36, 0.15); color: var(--orange); }

.mt-2 { margin-top: 0.5rem; }
</style>
