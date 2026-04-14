<template>
  <div class="control-panel">
    <div class="panel-header">
      <h2>会议控制</h2>
      <div class="status-indicator" :class="{ active: isRunning || isFinalizing }">
        {{ statusText }}
      </div>
    </div>

    <div class="meeting-info" v-if="isRunning || isFinalizing">
      <div class="info-item">
        <span class="label">会议时长</span>
        <span class="value duration">{{ formattedDuration }}</span>
      </div>
      <div class="info-item">
        <span class="label">参与者</span>
        <span class="value">{{ participantCount }} 人</span>
      </div>
    </div>

    <div class="control-buttons">
      <button v-if="!isRunning && !isFinalizing" class="btn btn-primary btn-start" @click="handleStart" :disabled="isLoading">
        <span class="icon">▶</span>
        开始会议
      </button>
      <button v-else class="btn btn-danger btn-end" @click="handleEnd" :disabled="isLoading || isFinalizing">
        <span class="icon">■</span>
        {{ isFinalizing ? '正在结束...' : '结束会议' }}
      </button>
    </div>

    <div class="config-section">
      <h3>会议配置</h3>

      <div class="config-item">
        <label>音频目录</label>
        <input v-model="localConfig.inputDir" type="text" @change="handleConfigChange"
          placeholder="留空时使用网关默认 audio 目录" />
        <p class="config-hint">目录路径以 Gateway 所在机器为准</p>
      </div>

      <div class="config-item">
        <label>文件匹配模式</label>
        <input v-model="localConfig.globPattern" type="text" @change="handleConfigChange" placeholder="例如 *.m4a" />
      </div>

      <div class="config-item">
        <label>源语言</label>
        <CustomSelect v-model="localConfig.language" :options="languageOptions"
          @update:model-value="handleConfigChange" />
      </div>

      <div class="config-item">
        <label class="checkbox-label">
          <input type="checkbox" v-model="localConfig.translationEnabled" @change="handleConfigChange" />
          <span>启用实时翻译</span>
        </label>
      </div>

      <div class="config-item" v-if="localConfig.translationEnabled">
        <label>目标语言</label>
        <CustomSelect v-model="localConfig.targetLanguage" :options="targetLanguageOptions"
          :disabled="targetLanguageLocked" @update:model-value="handleConfigChange" />
        <p class="config-hint" v-if="targetLanguageLocked">会议进行中，目标语言仅可在会前修改</p>
      </div>

      <div class="config-item">
        <label class="checkbox-label">
          <input type="checkbox" v-model="localConfig.actionEnabled" @change="handleConfigChange" />
          <span>启用待办提取</span>
        </label>
      </div>

      <div class="config-item">
        <label class="checkbox-label">
          <input type="checkbox" v-model="localConfig.sentimentEnabled" @change="handleConfigChange" />
          <span>启用情感分析</span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch } from 'vue'
import { useMeetingStore } from '../stores/meeting'
import type { MeetingConfig } from '../types'
import CustomSelect from './CustomSelect.vue'
import { isTargetLanguageLocked } from '../stores/meetingMessageUtils'

const {
  isRunning,
  isFinalizing,
  formattedDuration,
  participantCount,
  config,
  startMeeting,
  endMeeting,
  updateConfig,
} = useMeetingStore()

const isLoading = ref(false)
const localConfig = reactive<MeetingConfig>({
  meetingId: '',
  inputDir: '',
  globPattern: '*.m4a',
  language: 'zh',
  translationEnabled: true,
  targetLanguage: 'en',
  actionEnabled: true,
  sentimentEnabled: true,
})

const languageOptions = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
]

const targetLanguageOptions = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日本語' },
]

const targetLanguageLocked = computed(() => isTargetLanguageLocked(isRunning.value))
const statusText = computed(() => {
  if (isFinalizing.value) {
    return '结束中'
  }
  return isRunning.value ? '进行中' : '未开始'
})

async function handleStart() {
  isLoading.value = true
  try {
    await startMeeting()
  } finally {
    isLoading.value = false
  }
}

async function handleEnd() {
  isLoading.value = true
  try {
    await endMeeting()
  } finally {
    isLoading.value = false
  }
}

function handleConfigChange() {
  updateConfig(localConfig)
}

watch(
  () => config.value,
  (newConfig) => {
    Object.assign(localConfig, newConfig)
  },
  { deep: true }
)
</script>

<style scoped>
.control-panel {
  background: var(--panel-gradient);
  border-radius: 16px;
  padding: 24px;
  min-height: var(--meeting-panel-min-height);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-card);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 600;
}

.status-indicator {
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 0.95rem;
  font-weight: 500;
  background: var(--bg-card-alt);
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.status-indicator.active {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: #fff;
  box-shadow: 0 0 20px rgba(14, 165, 233, 0.28);
}

.meeting-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--bg-card-alt);
  border-radius: 12px;
}

.info-item {
  text-align: center;
}

.info-item .label {
  display: block;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-item .value {
  font-size: 1.25rem;
  font-weight: 600;
}

.info-item .duration {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 1.5rem;
  color: var(--primary);
}

.control-buttons {
  margin-bottom: 24px;
}

.btn {
  width: 100%;
  padding: 16px 24px;
  border: none;
  border-radius: 12px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.32);
}

.btn-danger {
  background: linear-gradient(135deg, var(--danger) 0%, #b91c1c 100%);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(255, 107, 107, 0.4);
}

.btn .icon {
  font-size: 1.25rem;
}

.config-section h3 {
  margin: 0 0 16px 0;
  font-size: 1.05rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.config-item {
  margin-bottom: 16px;
}

.config-item label {
  display: block;
  margin-bottom: 8px;
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.config-item input[type="text"] {
  width: 100%;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-primary);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.95rem;
}

.config-item input[type="text"]:focus {
  outline: 2px solid rgba(14, 165, 233, 0.18);
  border-color: var(--primary);
}

.config-hint {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.checkbox-label span {
  font-size: 0.95rem;
  color: var(--text-secondary);
}
</style>
