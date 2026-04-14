<template>
  <div class="subtitle-panel">
    <div class="panel-header">
      <div class="panel-heading">
        <h2>实时字幕</h2>
        <p class="runtime-inline" v-if="showRuntimeMessage">{{ runtimeMessage }}</p>
      </div>
      <div class="subtitle-count" v-if="subtitles.length > 0">
        {{ subtitles.length }} 条记录
      </div>
    </div>

    <div class="realtime-sentiment-row" v-if="showRealtimeSentimentRow">
      <span class="runtime-label">实时情感</span>
      <div class="sentiment-chip-list">
        <div
          v-for="entry in latestRealtimeSentiments"
          :key="entry.speaker"
          class="sentiment-chip"
          :class="toneClass(entry.label)"
        >
          <span class="chip-speaker">{{ entry.speaker }}</span>
          <span class="chip-label">{{ entry.label }}</span>
          <span class="chip-signal" v-if="entry.signal">{{ entry.signal }}</span>
        </div>
      </div>
    </div>

    <div
      class="subtitle-container"
      ref="containerRef"
      tabindex="0"
      @focusin="handlePanelFocusIn"
      @focusout="handlePanelFocusOut"
      @scroll="handleSubtitleScroll"
    >
      <div v-if="subtitles.length > 0" class="subtitle-list-shell">
        <div class="subtitle-list" :style="{ height: `${totalSize}px` }">
          <div
            v-for="entry in virtualRows"
            :key="entry.subtitle.id"
            :data-index="entry.virtualRow.index"
            :ref="measureSubtitleElement"
            class="subtitle-item-wrapper"
            :style="{ transform: `translateY(${entry.virtualRow.start}px)` }"
          >
            <div class="subtitle-item">
              <div class="subtitle-meta">
                <span class="speaker">{{ entry.subtitle.speaker }}</span>
                <span class="time">{{ formatTime(entry.subtitle.timestamp) }}</span>
              </div>
              <div class="subtitle-content">
                <p class="original-text">{{ entry.subtitle.text }}</p>
                <p
                  v-if="entry.subtitle.translationDisplay.text"
                  class="translated-text"
                  :class="{ pending: entry.subtitle.translationDisplay.pending }"
                >
                  {{ entry.subtitle.translationDisplay.text }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">💬</div>
        <p v-if="liveError" class="error-text">{{ liveError }}</p>
        <p v-else-if="isRunning || isFinalizing">会议进行中，等待字幕数据...</p>
        <p v-else>等待会议开始...</p>
        <p class="hint" v-if="liveError">请检查网关日志，以及 M6 音频输入服务或 VCSum 回退模式配置</p>
        <p class="hint" v-else-if="isRunning || isFinalizing">请确认目录音频可读取，网关正在推送字幕流</p>
        <p class="hint" v-else>字幕将在会议开始后实时显示</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch, type ComponentPublicInstance } from 'vue'
import { useVirtualizer, type VirtualItem } from '@tanstack/vue-virtual'
import type { RealtimeSentimentEntry } from '../types'
import { useMeetingStore } from '../stores/meeting'
import { resolveSubtitleTranslationDisplay } from '../stores/meetingMessageUtils'

const {
  subtitles,
  config,
  isRunning,
  isFinalizing,
  liveError,
  runtimeInfoMessages,
  realtimeSentiments,
} = useMeetingStore()
const containerRef = ref<HTMLDivElement | null>(null)
const panelFocused = ref(false)
const historyPinned = ref(false)

type SubtitleWithTranslationState = {
  id: string
  speaker: string
  text: string
  timestamp: string
  translationDisplay: {
    text: string | null
    pending: boolean
  }
}

type VirtualSubtitleRow = {
  virtualRow: VirtualItem
  subtitle: SubtitleWithTranslationState
}

const subtitlesWithTranslationState = computed<SubtitleWithTranslationState[]>(() =>
  subtitles.value.map((subtitle) => ({
    id: subtitle.id,
    speaker: subtitle.speaker,
    text: subtitle.text,
    timestamp: subtitle.timestamp,
    translationDisplay: resolveSubtitleTranslationDisplay(
      config.value.translationEnabled,
      subtitle.translation,
    ),
  })),
)

// Keep the full subtitle history rendered efficiently instead of truncating old items.
const rowVirtualizer = useVirtualizer<HTMLDivElement, HTMLDivElement>(
  computed(() => ({
    count: subtitlesWithTranslationState.value.length,
    getScrollElement: () => containerRef.value,
    estimateSize: () => 144,
    overscan: 5,
    getItemKey: (index: number) =>
      subtitlesWithTranslationState.value[index]?.id ?? `subtitle-${index}`,
  })),
)

const virtualRows = computed<VirtualSubtitleRow[]>(() =>
  rowVirtualizer.value.getVirtualItems().reduce<VirtualSubtitleRow[]>((rows, virtualRow) => {
    const subtitle = subtitlesWithTranslationState.value[virtualRow.index]
    if (subtitle) {
      rows.push({ virtualRow, subtitle })
    }
    return rows
  }, []),
)

const totalSize = computed(() => rowVirtualizer.value.getTotalSize())
const latestRuntimeInfo = computed(() => runtimeInfoMessages.value.at(-1) ?? null)
const latestRealtimeSentiments = computed<RealtimeSentimentEntry[]>(() => {
  // Keep one latest tag per speaker instead of stacking duplicate speaker updates.
  const latestBySpeaker = new Map<string, RealtimeSentimentEntry>()
  for (const entry of realtimeSentiments.value) {
    latestBySpeaker.set(entry.speaker, entry)
  }

  return Array.from(latestBySpeaker.values()).sort((left, right) => {
    const leftTimestamp = typeof left.timestamp === 'number' ? left.timestamp : -1
    const rightTimestamp = typeof right.timestamp === 'number' ? right.timestamp : -1
    return rightTimestamp - leftTimestamp
  })
})
const showRuntimeMessage = computed(() =>
  isRunning.value
  || isFinalizing.value
  || runtimeInfoMessages.value.length > 0,
)
const showRealtimeSentimentRow = computed(() =>
  config.value.sentimentEnabled && latestRealtimeSentiments.value.length > 0,
)
const runtimeMessage = computed(() => {
  if (latestRuntimeInfo.value?.message) {
    return latestRuntimeInfo.value.message
  }
  if (isFinalizing.value) {
    return '正在基于已输出内容整理会后结果...'
  }
  if (isRunning.value) {
    return '等待网关状态消息...'
  }
  return ''
})

function measureSubtitleElement(
  element: Element | ComponentPublicInstance | null,
) {
  if (element instanceof Element) {
    rowVirtualizer.value.measureElement(element as HTMLDivElement)
  }
}

function isNearLiveEdge(): boolean {
  const container = containerRef.value
  if (!container) {
    return true
  }

  return container.scrollHeight - (container.scrollTop + container.clientHeight) <= 48
}

function handleSubtitleScroll(): void {
  historyPinned.value = !isNearLiveEdge()
}

function handlePanelFocusIn(): void {
  panelFocused.value = true
}

function handlePanelFocusOut(): void {
  panelFocused.value = false
  historyPinned.value = !isNearLiveEdge()
}

function formatAudioSeconds(rawTimestamp: string): string | null {
  const totalSeconds = Number(rawTimestamp)
  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) {
    return null
  }

  const totalMilliseconds = Math.round(totalSeconds * 1000)
  const hours = Math.floor(totalMilliseconds / 3_600_000)
  const minutes = Math.floor((totalMilliseconds % 3_600_000) / 60_000)
  const seconds = Math.floor((totalMilliseconds % 60_000) / 1000)
  const milliseconds = totalMilliseconds % 1000
  const baseTime = hours > 0
    ? `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    : `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`

  return `${baseTime}.${milliseconds.toString().padStart(3, '0')}`
}

function formatTime(timestamp: string): string {
  // Audio-first mode sends floating-point seconds, while VCSum keeps ISO timestamps.
  const audioTime = formatAudioSeconds(timestamp.trim())
  if (audioTime) {
    return audioTime
  }

  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) {
    return '时间未知'
  }

  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function toneClass(label: string): string {
  const normalized = label.toLowerCase()
  if (normalized.includes('positive')) {
    return 'tone-positive'
  }
  if (normalized.includes('negative')) {
    return 'tone-negative'
  }
  return 'tone-neutral'
}

watch(
  () => subtitles.value.length,
  async (count, previousCount) => {
    if (count === 0) {
      panelFocused.value = false
      historyPinned.value = false
      return
    }

    if (count <= previousCount || panelFocused.value || historyPinned.value) {
      return
    }

    await nextTick()
    // Only follow the stream while the viewer stays at the live edge.
    rowVirtualizer.value.scrollToIndex(count - 1, { align: 'start' })
  },
)
</script>

<style scoped>
.subtitle-panel {
  background: var(--panel-gradient);
  border-radius: 16px;
  padding: 24px;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 900px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
}

.runtime-inline {
  margin: 0;
  min-width: 0;
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.subtitle-count {
  font-size: 0.85rem;
  color: var(--text-secondary);
  background: var(--bg-card-alt);
  padding: 4px 12px;
  border-radius: 12px;
}

.subtitle-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.subtitle-container:focus-visible {
  outline: 2px solid rgba(14, 165, 233, 0.28);
  outline-offset: 4px;
}

.realtime-sentiment-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  min-width: 0;
}

.runtime-label {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
}

.sentiment-chip-list {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  min-width: 0;
  overflow-x: auto;
  padding-bottom: 4px;
}

.sentiment-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  line-height: 1.2;
  background: rgba(14, 165, 233, 0.08);
  color: #075985;
  white-space: nowrap;
}

.sentiment-chip.tone-positive {
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
}

.sentiment-chip.tone-negative {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

.sentiment-chip.tone-neutral {
  background: rgba(217, 119, 6, 0.1);
  color: #b45309;
}

.chip-speaker {
  font-weight: 600;
}

.chip-signal {
  color: inherit;
  opacity: 0.78;
}

.subtitle-list-shell {
  min-height: 100%;
  padding-bottom: 12px;
}

.subtitle-list {
  position: relative;
  width: 100%;
}

.subtitle-item-wrapper {
  left: 0;
  position: absolute;
  top: 0;
  width: 100%;
  padding-bottom: 12px;
}

.subtitle-item {
  background: var(--bg-card-alt);
  border-radius: 12px;
  padding: 16px;
  border-left: 3px solid var(--primary);
}

.subtitle-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.speaker {
  font-weight: 600;
  color: var(--primary);
  font-size: 0.95rem;
}

.time {
  font-size: 0.85rem;
  color: var(--text-muted);
  font-family: 'SF Mono', 'Consolas', monospace;
}

.subtitle-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.original-text {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.5;
  color: var(--text-primary);
}

.translated-text {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-secondary);
  font-style: italic;
  padding-left: 12px;
  border-left: 2px solid rgba(14, 165, 233, 0.35);
}

.translated-text.pending {
  color: var(--text-muted);
  font-style: normal;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
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

.error-text {
  color: #dc2626;
  font-weight: 600;
}
</style>
