<template>
  <div class="app-container">
    <header class="app-header">
      <div class="logo">
        <span class="logo-icon">🎙️</span>
        <h1>智能会议助手</h1>
      </div>
      <div class="header-status">
        <span class="status-dot" :class="{ active: isRunning || isFinalizing }"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </header>

    <main class="app-main">
      <div class="dashboard-grid">
        <aside class="sidebar">
          <ControlPanel />
        </aside>

        <section class="content-area">
          <div class="realtime-section" v-if="showRuntimeSurface">
            <div class="panel-row">
              <SubtitlePanel />
            </div>
          </div>

          <div class="summary-section" v-if="showSummary">
            <div ref="summaryPanelRowRef" class="summary-panel-row">
              <SummaryPanel />
              <SentimentPanel v-if="config.sentimentEnabled" />
            </div>
          </div>

          <div class="welcome-section" v-if="!showRuntimeSurface && !showSummary">
            <div class="welcome-content">
              <div class="welcome-icon">🎙️</div>
              <h2>欢迎使用智能会议助手</h2>
              <p>点击"开始会议"按钮开始您的智能会议体验</p>
              <div class="features">
                <div class="feature-item">
                  <span class="feature-icon">💬</span>
                  <span class="feature-text">实时字幕</span>
                </div>
                <div class="feature-item">
                  <span class="feature-icon">🌐</span>
                  <span class="feature-text">智能翻译</span>
                </div>
                <div class="feature-item">
                  <span class="feature-icon">📊</span>
                  <span class="feature-text">情感分析</span>
                </div>
                <div class="feature-item">
                  <span class="feature-icon">📝</span>
                  <span class="feature-text">会议总结</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useMeetingStore } from './stores/meeting'
import ControlPanel from './components/ControlPanel.vue'
import SubtitlePanel from './components/SubtitlePanel.vue'
import SentimentPanel from './components/SentimentPanel.vue'
import SummaryPanel from './components/SummaryPanel.vue'

const { isRunning, isFinalizing, showRuntimeSurface, config, summary, summaryStatus } = useMeetingStore()
const summaryPanelRowRef = ref<HTMLDivElement | null>(null)

let panelHeightObserver: ResizeObserver | null = null
let syncedResultPanelHeight = 0

const showSummary = computed(() => {
  if (showRuntimeSurface.value) {
    return false
  }
  return summaryStatus.value !== 'idle' || summary.value !== null
})

const statusText = computed(() => {
  if (isFinalizing.value) {
    return '会议结束中'
  }
  return isRunning.value ? '会议进行中' : '等待开始'
})

function clearResultPanelMinHeight(): void {
  const row = summaryPanelRowRef.value
  if (!row) {
    syncedResultPanelHeight = 0
    return
  }

  row.querySelectorAll<HTMLElement>('.summary-panel, .sentiment-panel').forEach((panel) => {
    panel.style.removeProperty('min-height')
  })
  syncedResultPanelHeight = 0
}

function syncResultPanelHeights(): void {
  const row = summaryPanelRowRef.value
  if (!row || !showSummary.value || !config.value.sentimentEnabled) {
    clearResultPanelMinHeight()
    return
  }

  const panels = Array.from(
    row.querySelectorAll<HTMLElement>('.summary-panel, .sentiment-panel'),
  )
  if (panels.length < 2) {
    clearResultPanelMinHeight()
    return
  }

  // Use measured scroll heights so both result panels stay aligned without duplicating layout rules.
  const nextHeight = Math.max(
    ...panels.map((panel) =>
      Math.ceil(Math.max(panel.scrollHeight, panel.getBoundingClientRect().height)),
    ),
  )
  if (!nextHeight || nextHeight === syncedResultPanelHeight) {
    return
  }

  syncedResultPanelHeight = nextHeight
  panels.forEach((panel) => {
    panel.style.minHeight = `${nextHeight}px`
  })
}

function observeResultPanelHeights(): void {
  panelHeightObserver?.disconnect()

  const row = summaryPanelRowRef.value
  if (!row || !showSummary.value || !config.value.sentimentEnabled) {
    clearResultPanelMinHeight()
    return
  }

  panelHeightObserver = new ResizeObserver(() => {
    requestAnimationFrame(() => syncResultPanelHeights())
  })

  row.querySelectorAll<HTMLElement>('.summary-panel, .sentiment-panel').forEach((panel) => {
    panelHeightObserver?.observe(panel)
  })
  syncResultPanelHeights()
}

watch(
  [showSummary, () => config.value.sentimentEnabled],
  async () => {
    await nextTick()
    observeResultPanelHeights()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  panelHeightObserver?.disconnect()
  clearResultPanelMinHeight()
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 1.75rem;
}

.logo h1 {
  font-size: 1.65rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all 0.3s ease;
}

.status-dot.active {
  background: var(--primary);
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.35);
  animation: pulse 2s infinite;
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.6;
  }
}

.status-text {
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.app-main {
  flex: 1;
  padding: 24px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto;
  height: 100%;
}

.sidebar {
  position: sticky;
  top: 100px;
  height: fit-content;
}

.content-area {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-height: 0;
}

.realtime-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.panel-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.summary-panel-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  align-items: stretch;
}

.welcome-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 200px);
}

.welcome-content {
  text-align: center;
  max-width: 600px;
}

.welcome-icon {
  font-size: 5rem;
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {

  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-10px);
  }
}

.welcome-content h2 {
  font-size: 2.2rem;
  margin-bottom: 16px;
  background: linear-gradient(135deg, var(--text-primary) 0%, #334155 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-content p {
  font-size: 1.2rem;
  color: var(--text-secondary);
  margin-bottom: 48px;
}

.features {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: var(--bg-card);
  border-radius: 16px;
  border: 1px solid var(--border-color);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: var(--bg-card-alt);
  transform: translateY(-4px);
}

.feature-icon {
  font-size: 2rem;
}

.feature-text {
  font-size: 0.95rem;
  color: var(--text-secondary);
}

@media (max-width: 1200px) {
  .summary-panel-row {
    grid-template-columns: 1fr;
    min-height: auto;
  }
}

@media (max-width: 900px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: static;
  }

  .features {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .app-header {
    padding: 12px 16px;
  }

  .logo h1 {
    font-size: 1.25rem;
  }

  .app-main {
    padding: 16px;
  }

  .features {
    grid-template-columns: 1fr;
  }
}
</style>
