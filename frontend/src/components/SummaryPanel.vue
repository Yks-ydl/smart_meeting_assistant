<template>
  <div class="summary-panel">
    <div class="panel-header" v-if="!summary">
      <h2>会议总结</h2>
    </div>

    <div class="loading-state" v-if="summaryStatus === 'loading'">
      <div class="loading-icon">⏳</div>
      <p>正在生成会议总结...</p>
      <p class="hint">请稍候，系统正在整理摘要与行动项</p>
    </div>

    <div class="summary-content" v-else-if="summary">
      <div class="summary-header">
        <h3 class="meeting-title">{{ summary.title }}</h3>
        <div class="meeting-meta">
          <span class="meta-item">
            <span class="icon">📅</span>
            {{ formatDate(summary.generatedAt) }}
          </span>
          <span class="meta-item">
            <span class="icon">⏱️</span>
            {{ formatDuration(summary.duration) }}
          </span>
          <span class="meta-item">
            <span class="icon">👥</span>
            {{ uniqueParticipants.length }} 人参与
          </span>
        </div>
      </div>

      <div class="summary-section">
        <h4>会议摘要</h4>
        <div class="markdown-content" v-html="renderedSummary"></div>
      </div>

      <div class="summary-section">
        <h4>关键要点</h4>
        <ul class="key-points">
          <li v-for="(point, index) in summary.keyPoints" :key="index">
            <div class="markdown-content point-content" v-html="renderMarkdown(point)"></div>
          </li>
        </ul>
      </div>

      <div class="summary-section">
        <h4>行动项</h4>
        <div class="action-items" v-if="summary.actionItems.length > 0">
          <div v-for="item in summary.actionItems" :key="item.id" class="action-item"
            :class="`priority-${item.priority}`">
            <div class="action-header">
              <span class="action-task">{{ item.task }}</span>
              <span class="priority-badge" :class="item.priority">
                {{ priorityText(item.priority) }}
              </span>
            </div>
            <div class="action-meta" v-if="item.assignee || item.dueDate">
              <span v-if="item.assignee" class="meta-tag">
                <span class="icon">👤</span>
                {{ item.assignee }}
              </span>
              <span v-if="item.dueDate" class="meta-tag">
                <span class="icon">📆</span>
                {{ item.dueDate }}
              </span>
            </div>
          </div>
        </div>
        <div class="empty-actions" v-else>未识别到行动项</div>
      </div>

      <div class="summary-section">
        <h4>参与者</h4>
        <div class="participants">
          <span v-for="participant in uniqueParticipants" :key="participant" class="participant-tag">
            {{ participant }}
          </span>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else-if="summaryStatus === 'error'">
      <div class="empty-icon">⚠️</div>
      <p>会议总结生成失败</p>
      <p class="hint">{{ summaryError || '请稍后重试' }}</p>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📝</div>
      <p>暂无会议总结</p>
      <p class="hint">会议结束后将自动生成总结</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import { useMeetingStore } from '../stores/meeting'

const { summary, summaryStatus, summaryError } = useMeetingStore()
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })

const renderedSummary = computed(() => {
  if (!summary.value?.summary) return ''
  return markdown.render(summary.value.summary)
})

const uniqueParticipants = computed(() => {
  // 必须使用 summary.value 来访问 ref 里的实际数据
  if (!summary.value?.participants) return []
  return Array.from(new Set(summary.value.participants)).sort()
})

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟`
  } else if (secs > 0) {
    return `${secs}秒`
  }
  return "不到1分钟"
}

function priorityText(priority: string): string {
  const map: Record<string, string> = {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级',
  }
  return map[priority] || priority
}

function renderMarkdown(text: string): string {
  return markdown.render(text || '')
}
</script>

<style scoped>
.summary-panel {
  background: var(--panel-gradient);
  border-radius: 16px;
  padding: 24px;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-card);
}

.panel-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 24px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 600;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.summary-header {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.meeting-title {
  margin: 0 0 12px 0;
  font-size: 1.55rem;
  font-weight: 600;
  color: var(--text-primary);
}

.meeting-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.meta-item .icon {
  font-size: 1rem;
}

.summary-section h4 {
  margin: 0 0 12px 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--primary);
}

.summary-text {
  margin: 0;
  font-size: 1rem;
  line-height: 1.7;
  color: var(--text-secondary);
}

.markdown-content {
  color: var(--text-secondary);
  line-height: 1.7;
}

.markdown-content :deep(p) {
  margin: 0 0 10px 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0;
  padding-left: 20px;
}

.markdown-content :deep(code) {
  background: var(--bg-card-alt);
  border: 1px solid var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
}

.point-content :deep(p) {
  margin: 0;
}

.key-points {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-points li {
  font-size: 1rem;
  line-height: 1.5;
  color: var(--text-secondary);
}

.action-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-actions {
  color: var(--text-secondary);
  font-size: 0.95rem;
}

.action-item {
  background: var(--bg-card-alt);
  border-radius: 12px;
  padding: 16px;
  border-left: 3px solid;
}

.action-item.priority-high {
  border-left-color: #ff6b6b;
}

.action-item.priority-medium {
  border-left-color: #ffc107;
}

.action-item.priority-low {
  border-left-color: var(--primary);
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.action-task {
  font-size: 1rem;
  color: var(--text-primary);
  flex: 1;
}

.priority-badge {
  font-size: 0.8rem;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
}

.priority-badge.high {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

.priority-badge.medium {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.priority-badge.low {
  background: rgba(14, 165, 233, 0.16);
  color: var(--primary);
}

.action-meta {
  display: flex;
  gap: 16px;
}

.meta-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.meta-tag .icon {
  font-size: 0.875rem;
}

.participants {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.participant-tag {
  background: rgba(14, 165, 233, 0.14);
  color: var(--primary);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: var(--meeting-panel-min-height);
  color: var(--text-muted);
  text-align: center;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: var(--meeting-panel-min-height);
  text-align: center;
  color: var(--text-secondary);
}

.loading-icon {
  font-size: 2.8rem;
  margin-bottom: 12px;
  animation: spin 1.8s linear infinite;
}

.loading-state .hint {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 8px;
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
