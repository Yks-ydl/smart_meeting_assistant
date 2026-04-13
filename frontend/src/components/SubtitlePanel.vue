<template>
  <div class="subtitle-panel">
    <div class="panel-header">
      <h2>实时字幕</h2>
      <div class="subtitle-count" v-if="subtitles.length > 0">
        {{ subtitles.length }} 条记录
      </div>
    </div>

    <div class="subtitle-container" ref="containerRef">
      <TransitionGroup name="subtitle-list" tag="div" class="subtitle-list">
        <div v-for="subtitle in subtitlesWithTranslationState" :key="subtitle.id" class="subtitle-item">
          <div class="subtitle-meta">
            <span class="speaker">{{ subtitle.speaker }}</span>
            <span class="time">{{ formatTime(subtitle.timestamp) }}</span>
          </div>
          <div class="subtitle-content">
            <p class="original-text">{{ subtitle.text }}</p>
            <p
              class="translated-text"
              :class="{ pending: subtitle.translationDisplay.pending }"
              v-if="subtitle.translationDisplay.text"
            >
              {{ subtitle.translationDisplay.text }}
            </p>
          </div>
        </div>
      </TransitionGroup>

      <div class="empty-state" v-if="subtitles.length === 0">
        <div class="empty-icon">💬</div>
        <p v-if="liveError" class="error-text">{{ liveError }}</p>
        <p v-else-if="isRunning">会议进行中，等待字幕数据...</p>
        <p v-else>等待会议开始...</p>
        <p class="hint" v-if="liveError">请检查网关日志，以及 M6 音频输入服务或 VCSum 回退模式配置</p>
        <p class="hint" v-else-if="isRunning">请确认目录音频可读取，网关正在推送字幕流</p>
        <p class="hint" v-else>字幕将在会议开始后实时显示</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { useMeetingStore } from '../stores/meeting'
import { resolveSubtitleTranslationDisplay } from '../stores/meetingMessageUtils'

const { subtitles, config, isRunning, liveError } = useMeetingStore()
const containerRef = ref<HTMLElement | null>(null)

const subtitlesWithTranslationState = computed(() =>
  subtitles.value.map((subtitle) => ({
    ...subtitle,
    translationDisplay: resolveSubtitleTranslationDisplay(
      config.value.translationEnabled,
      subtitle.translation,
    ),
  })),
)

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

watch(
  () => subtitles.value.length,
  async () => {
    await nextTick()
    if (containerRef.value) {
      containerRef.value.scrollTop = containerRef.value.scrollHeight
    }
  }
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
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
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
  scrollbar-width: none;
  /* Firefox */
  -ms-overflow-style: none;
  /* IE and Edge */
}

.subtitle-container::-webkit-scrollbar {
  display: none;
  /* Chrome, Safari and Opera */
}

.subtitle-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subtitle-item {
  background: var(--bg-card-alt);
  border-radius: 12px;
  padding: 16px;
  border-left: 3px solid var(--primary);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
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

.subtitle-list-enter-active,
.subtitle-list-leave-active {
  transition: all 0.3s ease;
}

.subtitle-list-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.subtitle-list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
