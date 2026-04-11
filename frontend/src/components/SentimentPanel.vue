<template>
  <div class="sentiment-panel">
    <div class="panel-header">
      <h2>情感分析仪表盘</h2>
    </div>

    <div class="sentiment-content" v-if="sentiment">
      <div class="overall-sentiment">
        <div class="sentiment-gauge">
          <svg viewBox="0 0 200 120" class="gauge-svg">
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(15, 23, 42, 0.12)" stroke-width="12"
              stroke-linecap="round" />
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" :stroke="gaugeColor" stroke-width="12"
              stroke-linecap="round" :stroke-dasharray="gaugeDash" class="gauge-fill" />
          </svg>
          <div class="gauge-value">
            <span class="value">{{ (sentiment.overall * 100).toFixed(0) }}</span>
            <span class="unit">%</span>
          </div>
        </div>
        <div class="sentiment-label">
          <span class="label" :style="{ color: gaugeColor }">{{ sentimentText }}</span>
          <span class="sublabel">整体情感指数</span>
        </div>
      </div>

      <div class="sentiment-bars">
        <div class="bar-item">
          <div class="bar-header">
            <span class="bar-label">积极</span>
            <span class="bar-value">{{ (sentiment.positive * 100).toFixed(0) }}%</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill positive" :style="{ width: `${sentiment.positive * 100}%` }"></div>
          </div>
        </div>

        <div class="bar-item">
          <div class="bar-header">
            <span class="bar-label">中性</span>
            <span class="bar-value">{{ (sentiment.neutral * 100).toFixed(0) }}%</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill neutral" :style="{ width: `${sentiment.neutral * 100}%` }"></div>
          </div>
        </div>

        <div class="bar-item">
          <div class="bar-header">
            <span class="bar-label">消极</span>
            <span class="bar-value">{{ (sentiment.negative * 100).toFixed(0) }}%</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill negative" :style="{ width: `${sentiment.negative * 100}%` }"></div>
          </div>
        </div>
      </div>

      <div class="engagement-section">
        <div class="engagement-header">
          <span class="label">参与度</span>
          <span class="value">{{ (sentiment.engagement * 100).toFixed(0) }}%</span>
        </div>
        <div class="engagement-bar">
          <div class="engagement-fill" :style="{ width: `${sentiment.engagement * 100}%` }"></div>
        </div>
      </div>

      <div class="trend-section" v-if="sentiment.trend.length > 1">
        <h3>情感趋势</h3>
        <div class="trend-chart">
          <svg viewBox="0 0 300 80" class="trend-svg">
            <polyline :points="trendPoints" fill="none" stroke="#0ea5e9" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round" />
            <circle v-for="(point, index) in trendCirclePoints" :key="index" :cx="point.x" :cy="point.y" r="3"
              fill="#0ea5e9" />
          </svg>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📊</div>
      <p v-if="sentimentStatus === 'stalled'">情感数据暂未返回</p>
      <p v-else-if="sentimentStatus === 'waiting'">正在接收情感数据...</p>
      <p v-else>等待会议开始...</p>
      <p class="hint" v-if="sentimentStatus === 'stalled'">
        已接收 {{ subtitleCount }} 条字幕，但尚未收到情感结果
      </p>
      <p class="hint" v-else>会议开始后将实时分析情感</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMeetingStore } from '../stores/meeting'

const { currentSentiment, sentimentStatus, subtitles } = useMeetingStore()

const sentiment = computed(() => currentSentiment.value)
const subtitleCount = computed(() => subtitles.value.length)

const gaugeColor = computed(() => {
  if (!sentiment.value) return '#64748b'
  const value = sentiment.value.overall
  if (value >= 0.7) return '#0ea5e9'
  if (value >= 0.4) return '#d97706'
  return '#dc2626'
})

const sentimentText = computed(() => {
  if (!sentiment.value) return '未知'
  const value = sentiment.value.overall
  if (value >= 0.7) return '积极'
  if (value >= 0.4) return '中性'
  return '消极'
})

const gaugeDash = computed(() => {
  if (!sentiment.value) return '0 251'
  const value = sentiment.value.overall
  const circumference = 251
  const dashLength = value * circumference
  return `${dashLength} ${circumference}`
})

const trendPoints = computed(() => {
  if (!sentiment.value || sentiment.value.trend.length < 2) return ''
  const trend = sentiment.value.trend
  const width = 300
  const height = 80
  const padding = 10

  return trend
    .map((point, index) => {
      const x = padding + (index / (trend.length - 1)) * (width - 2 * padding)
      const y = height - padding - point.value * (height - 2 * padding)
      return `${x},${y}`
    })
    .join(' ')
})

const trendCirclePoints = computed(() => {
  if (!sentiment.value || sentiment.value.trend.length < 2) return []
  const trend = sentiment.value.trend
  const width = 300
  const height = 80
  const padding = 10

  return trend.map((point, index) => ({
    x: padding + (index / (trend.length - 1)) * (width - 2 * padding),
    y: height - padding - point.value * (height - 2 * padding),
  }))
})
</script>

<style scoped>
.sentiment-panel {
  background: var(--panel-gradient);
  border-radius: 16px;
  padding: 24px;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  margin-bottom: 24px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
}

.sentiment-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.overall-sentiment {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.sentiment-gauge {
  position: relative;
  width: 180px;
}

.gauge-svg {
  width: 100%;
  height: auto;
}

.gauge-fill {
  transition: stroke-dasharray 0.5s ease;
}

.gauge-value {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}

.gauge-value .value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
}

.gauge-value .unit {
  font-size: 1rem;
  color: var(--text-secondary);
}

.sentiment-label {
  text-align: center;
}

.sentiment-label .label {
  font-size: 1.25rem;
  font-weight: 600;
  display: block;
}

.sentiment-label .sublabel {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.sentiment-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
}

.bar-label {
  color: var(--text-secondary);
}

.bar-value {
  color: var(--text-primary);
  font-weight: 500;
}

.bar-track {
  height: 8px;
  background: rgba(15, 23, 42, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.bar-fill.positive {
  background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%);
}

.bar-fill.neutral {
  background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
}

.bar-fill.negative {
  background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
}

.engagement-section {
  padding: 16px;
  background: var(--bg-card-alt);
  border-radius: 12px;
}

.engagement-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.engagement-header .label {
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.engagement-header .value {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--primary);
}

.engagement-bar {
  height: 12px;
  background: rgba(15, 23, 42, 0.1);
  border-radius: 6px;
  overflow: hidden;
}

.engagement-fill {
  height: 100%;
  background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.trend-section h3 {
  margin: 0 0 12px 0;
  font-size: 0.95rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.trend-chart {
  background: var(--bg-card-alt);
  border-radius: 8px;
  padding: 12px;
}

.trend-svg {
  width: 100%;
  height: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--text-muted);
  text-align: center;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
}

.empty-state .hint {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-top: 8px;
}
</style>
