<template>
  <div class="sentiment-panel">
    <div class="panel-header">
      <h2>会议情感分析</h2>
    </div>

    <div class="sentiment-content" v-if="sentiment">
      <div class="overview-grid">
        <div class="overview-card">
          <p class="metric-label">发言轮次</p>
          <p class="metric-value">{{ sentiment.overall_summary.total_turns }}</p>
        </div>

        <div class="overview-card">
          <p class="metric-label">会议氛围</p>
          <p class="metric-value" :class="atmosphereTone">
            {{ sentiment.overall_summary.atmosphere }}
          </p>
        </div>
      </div>

      <div class="signals-section">
        <h3>主导交互信号</h3>
        <div class="signal-tags" v-if="dominantSignals.length > 0">
          <span class="signal-tag" v-for="signal in dominantSignals" :key="signal">
            {{ signal }}
          </span>
        </div>
        <p class="empty-copy" v-else>暂无主导交互信号</p>
      </div>

      <div class="profiles-section" v-if="speakerProfiles.length > 0">
        <h3>发言人画像</h3>
        <div class="profiles-grid">
          <article class="profile-card" v-for="[speaker, profile] in speakerProfiles" :key="speaker">
            <p class="speaker-name">{{ speaker }}</p>
            <p>发言次数：{{ profile.participation_count }}</p>
            <p>主情绪：{{ profile.top_emotion }}</p>
            <p>主要行为：{{ profile.primary_behavior }}</p>
            <p>插话次数：{{ profile.interruption_count }}</p>
          </article>
        </div>
      </div>

      <div class="moments-section">
        <h3>显著时刻</h3>
        <ul class="moment-list" v-if="sentiment.significant_moments.length > 0">
          <li class="moment-item" v-for="(moment, index) in sentiment.significant_moments" :key="`${moment.speaker}-${index}`">
            <div class="moment-meta">
              <span class="moment-speaker">{{ moment.speaker }}</span>
              <span class="moment-time">{{ formatTimestamp(moment.timestamp) }}</span>
            </div>
            <p class="moment-snippet">{{ moment.snippet || '（无文本片段）' }}</p>
            <p class="moment-reason">
              原因：{{ moment.reason.length > 0 ? moment.reason.join(' / ') : '未标注' }}
            </p>
          </li>
        </ul>
        <p class="empty-copy" v-else>未检测到显著时刻</p>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📊</div>
      <p v-if="sentimentStatus === 'waiting'">会议进行中，等待会后情感汇总...</p>
      <p v-else-if="sentimentStatus === 'error'">情感分析生成失败</p>
      <p v-else>等待会议开始...</p>
      <p class="hint" v-if="sentimentStatus === 'error'">
        请确认 M4 服务已启动且返回格式符合接口文档
      </p>
      <p class="hint" v-else>
        情感分析将在会议结束后基于完整字幕生成
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SentimentSignificantMoment } from '../types'
import { useMeetingStore } from '../stores/meeting'

const { currentSentiment, sentimentStatus } = useMeetingStore()

const sentiment = computed(() => currentSentiment.value)

const dominantSignals = computed(() => sentiment.value?.overall_summary.dominant_signals ?? [])

const speakerProfiles = computed(() => {
  if (!sentiment.value) return []
  return Object.entries(sentiment.value.speaker_profiles)
})

const atmosphereTone = computed(() => {
  const atmosphere = sentiment.value?.overall_summary.atmosphere ?? ''
  const normalized = atmosphere.toLowerCase()
  if (normalized.includes('positive') || normalized.includes('constructive')) {
    return 'tone-positive'
  }
  if (normalized.includes('critical') || normalized.includes('tense')) {
    return 'tone-critical'
  }
  return 'tone-neutral'
})

function formatTimestamp(timestamp: SentimentSignificantMoment['timestamp']): string {
  if (Array.isArray(timestamp) && timestamp.length >= 2) {
    return `${timestamp[0].toFixed(1)}s - ${timestamp[1].toFixed(1)}s`
  }
  return typeof timestamp === 'string' ? timestamp : '未知'
}
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
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
}

.sentiment-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.overview-card {
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px;
}

.metric-label {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.metric-value {
  margin: 8px 0 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.tone-positive {
  color: #0ea5e9;
}

.tone-critical {
  color: #dc2626;
}

.tone-neutral {
  color: #d97706;
}

.signals-section h3,
.profiles-section h3,
.moments-section h3 {
  margin: 0 0 10px;
  font-size: 0.95rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.signal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.signal-tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
  font-size: 0.82rem;
}

.profiles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.profile-card {
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 12px;
}

.profile-card p {
  margin: 0 0 6px;
  font-size: 0.9rem;
}

.profile-card p:last-child {
  margin-bottom: 0;
}

.speaker-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.moment-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.moment-item {
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 12px;
}

.moment-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.moment-speaker {
  font-weight: 600;
}

.moment-time {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.moment-snippet,
.moment-reason {
  margin: 0;
  font-size: 0.9rem;
}

.moment-reason {
  margin-top: 4px;
  color: var(--text-secondary);
}

.empty-copy {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 220px;
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

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
