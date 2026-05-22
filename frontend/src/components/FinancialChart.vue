<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import type { MarketDataItem } from '@/types'

const props = defineProps<{
  data: MarketDataItem[]
  assetType: 'stock' | 'fund'
  height?: number
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const ranges = [
  { label: '1月', days: 30 },
  { label: '3月', days: 90 },
  { label: '6月', days: 180 },
  { label: '1年', days: 365 },
  { label: '全部', days: 0 },
]
const activeRange = ref(3) // default 1年

const filteredData = computed(() => {
  if (!props.data || props.data.length === 0) return []
  const sorted = [...props.data].sort((a, b) => a.date.localeCompare(b.date))
  const range = ranges[activeRange.value]
  if (!range || range.days === 0) return sorted
  // 从最后一个数据日期往前截取，而非基于当前日期
  const lastDate = new Date(sorted[sorted.length - 1].date)
  const cutoff = new Date(lastDate)
  cutoff.setDate(cutoff.getDate() - range.days)
  return sorted.filter(d => new Date(d.date) >= cutoff)
})

function initChart() {
  if (!chartRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)
  renderChart()
}

function renderChart() {
  if (!chart || filteredData.value.length === 0) return
  const dates = filteredData.value.map(d => d.date)
  const isStock = props.assetType === 'stock'

  if (isStock && filteredData.value[0]?.open !== undefined) {
    // Candlestick + Volume chart for stocks
    const ohlc = filteredData.value.map(d => [d.open, d.close, d.low, d.high])
    const volumes = filteredData.value.map(d => d.volume)

    const ma5 = calcMA(5)
    const ma20 = calcMA(20)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      grid: [
        { left: '8%', right: '8%', top: '8%', height: '55%' },
        { left: '8%', right: '8%', top: '72%', height: '18%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          axisLine: { onZero: false },
          axisLabel: { show: true, color: '#9aa0a6', fontSize: 10 },
          splitLine: { show: false },
          gridIndex: 0,
        },
        {
          type: 'category',
          data: dates,
          axisLabel: { show: false },
          gridIndex: 1,
        },
      ],
      yAxis: [
        {
          scale: true,
          splitArea: { show: true, areaStyle: { color: ['rgba(79,195,247,0.02)', 'rgba(79,195,247,0.05)'] } },
          axisLabel: { color: '#9aa0a6', fontSize: 10 },
          splitLine: { lineStyle: { color: '#2a2e3a' } },
          gridIndex: 0,
        },
        {
          scale: true,
          axisLabel: { show: true, color: '#9aa0a6', fontSize: 10 },
          splitLine: { show: false },
          gridIndex: 1,
        },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          start: 0,
          end: 100,
          height: 16,
          bottom: 4,
          borderColor: '#2a2e3a',
          backgroundColor: '#1a1d28',
          fillerColor: 'rgba(79,195,247,0.15)',
          handleStyle: { borderColor: '#4fc3f7' },
          textStyle: { color: '#9aa0a6' },
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: ohlc,
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: {
            color: '#34d399',
            color0: '#f87171',
            borderColor: '#34d399',
            borderColor0: '#f87171',
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              { type: 'max', label: { color: '#9aa0a6', fontSize: 10 } },
              { type: 'min', label: { color: '#9aa0a6', fontSize: 10 } },
            ],
          },
        },
        {
          name: 'MA5',
          type: 'line',
          data: ma5,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#fbbf24' },
        },
        {
          name: 'MA20',
          type: 'line',
          data: ma20,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: '#a78bfa' },
        },
        {
          name: '成交量',
          type: 'bar',
          data: volumes,
          xAxisIndex: 1,
          yAxisIndex: 1,
          itemStyle: {
            color: (params: any) => {
              const idx = params.dataIndex
              const d = filteredData.value[idx]
              return d.close >= d.open ? '#34d399' : '#f87171'
            },
          },
        },
      ],
    }, true)
  } else {
    // Line chart for funds
    const closeData = filteredData.value.map(d => d.close)

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      grid: { left: '8%', right: '8%', top: '8%', bottom: '15%' },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#9aa0a6', fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        scale: true,
        splitArea: { show: true, areaStyle: { color: ['rgba(79,195,247,0.02)', 'rgba(79,195,247,0.05)'] } },
        axisLabel: { color: '#9aa0a6', fontSize: 10 },
        splitLine: { lineStyle: { color: '#2a2e3a' } },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider', start: 0, end: 100, height: 16, bottom: 4,
          borderColor: '#2a2e3a', backgroundColor: '#1a1d28',
          fillerColor: 'rgba(79,195,247,0.15)',
          handleStyle: { borderColor: '#4fc3f7' },
          textStyle: { color: '#9aa0a6' },
        },
      ],
      series: [
        {
          name: '净值',
          type: 'line',
          data: closeData,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2, color: '#4fc3f7' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(79,195,247,0.3)' },
              { offset: 1, color: 'rgba(79,195,247,0.02)' },
            ]),
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              { type: 'max', label: { color: '#9aa0a6', fontSize: 10 } },
              { type: 'min', label: { color: '#9aa0a6', fontSize: 10 } },
            ],
          },
        },
      ],
    }, true)
  }
}

function calcMA(days: number): (number | null)[] {
  const close = filteredData.value.map(d => d.close)
  return close.map((_, i) => {
    if (i < days - 1) return null
    let sum = 0
    for (let j = i - days + 1; j <= i; j++) sum += close[j]
    return Math.round((sum / days) * 100) / 100
  })
}

function onResize() {
  chart?.resize()
}

function setRange(idx: number) {
  activeRange.value = idx
  renderChart()
}

watch(() => props.data, () => {
  if (chart) renderChart()
}, { deep: false })

onMounted(() => {
  if (props.data && props.data.length > 0) initChart()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div class="chart-wrapper">
    <div class="range-bar">
      <button
        v-for="(r, i) in ranges"
        :key="r.label"
        class="range-btn"
        :class="{ active: activeRange === i }"
        @click="setRange(i)"
      >{{ r.label }}</button>
    </div>
    <div ref="chartRef" class="chart-container" :style="{ height: height + 'px' || '360px' }"></div>
    <p v-if="!data || data.length === 0" class="text-secondary text-sm" style="text-align:center;padding:1rem;">暂无行情数据</p>
  </div>
</template>

<style scoped>
.chart-wrapper {
  width: 100%;
}
.range-bar {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 0.75rem;
}
.range-btn {
  padding: 0.25rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}
.range-btn:hover {
  color: var(--text);
  border-color: var(--accent);
}
.range-btn.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 600;
}
.chart-container {
  width: 100%;
  min-height: 280px;
}
</style>
