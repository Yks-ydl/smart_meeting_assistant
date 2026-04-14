import { ref, computed } from "vue";
import type {
  ActionItemDraft,
  MeetingConfig,
  PipelineStartRequest,
  RealtimeSentimentEntry,
  RuntimeActionWindow,
  RuntimeInfoEntry,
  SubtitleEntry,
  SentimentData,
  MeetingSummary,
} from "../types";
import { api } from "../services/api";
import {
  buildActionItems,
  deriveKeyPoints,
  extractAnalysisResultPayloads,
  mergeActionItemCollections,
  normalizeSentimentReport,
  normalizePipelineSubtitle,
  normalizeRealtimeSentimentEntry,
  normalizeRuntimeActionWindow,
  normalizeTargetLanguage,
} from "./meetingMessageUtils";

type SummaryStatus = "idle" | "loading" | "ready" | "error";
type SentimentStatus = "idle" | "waiting" | "ready" | "error";

const isRunning = ref(false);
const startTime = ref<string | null>(null);
const duration = ref(0);
const config = ref<MeetingConfig>({
  meetingId: "",
  inputDir: "",
  globPattern: "*.m4a",
  language: "zh",
  translationEnabled: true,
  targetLanguage: "en",
  actionEnabled: true,
  sentimentEnabled: true,
});

const subtitles = ref<SubtitleEntry[]>([]);
const currentSentiment = ref<SentimentData | null>(null);
const isFinalizing = ref(false);
const runtimeInfoMessages = ref<RuntimeInfoEntry[]>([]);
const runtimeActionWindows = ref<RuntimeActionWindow[]>([]);
const realtimeSentiments = ref<RealtimeSentimentEntry[]>([]);
const summary = ref<MeetingSummary | null>(null);
const summaryStatus = ref<SummaryStatus>("idle");
const summaryError = ref<string | null>(null);
const sentimentStatus = ref<SentimentStatus>("idle");
const liveError = ref<string | null>(null);

const formattedDuration = computed(() => {
  const hours = Math.floor(duration.value / 3600);
  const minutes = Math.floor((duration.value % 3600) / 60);
  const seconds = duration.value % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
});

const participantCount = computed(() => {
  const speakers = new Set<string>();
  subtitles.value.forEach((s) => {
    if (s.speaker) {
      speakers.add(s.speaker);
    }
  });
  return speakers.size;
});

let durationTimer: ReturnType<typeof setInterval> | null = null;

function pushRuntimeInfoMessage(message: string) {
  const normalized = message.trim();
  if (!normalized) {
    return;
  }

  runtimeInfoMessages.value = [
    ...runtimeInfoMessages.value.slice(-9),
    {
      id: `${Date.now()}-${runtimeInfoMessages.value.length}`,
      message: normalized,
      createdAt: new Date().toISOString(),
    },
  ];
}

function applyAsrPayload(raw: unknown) {
  const subtitle = normalizePipelineSubtitle(raw);
  if (!subtitle) {
    return;
  }

  subtitles.value.push(subtitle);
  liveError.value = null;
}

function applyTranslationPayload(raw: unknown) {
  const transData = raw as { subtitle_id?: string; translated_text?: string };
  if (
    !transData?.translated_text ||
    !transData.subtitle_id ||
    subtitles.value.length === 0
  ) {
    return;
  }

  const targetIndex = subtitles.value.findIndex(
    (sub) => sub.id === transData.subtitle_id,
  );
  if (targetIndex < 0) {
    return;
  }

  subtitles.value[targetIndex].translation = transData.translated_text;
}

function applySentimentPayload(raw: unknown) {
  const report = normalizeSentimentReport(raw);
  if (!report) {
    return;
  }

  currentSentiment.value = report;
  sentimentStatus.value = "ready";
}

function applyRealtimeSentimentPayload(raw: unknown, context?: unknown) {
  const realtimeSentiment = normalizeRealtimeSentimentEntry(raw, {
    speaker:
      typeof context === "object" && context !== null && "speaker" in context
        ? String((context as { speaker?: unknown }).speaker || "")
        : undefined,
    timestamp:
      typeof context === "object" && context !== null && "timestamp" in context
        ? (context as { timestamp?: unknown }).timestamp
        : undefined,
    subtitleId:
      typeof context === "object" && context !== null && "subtitle_id" in context
        ? String((context as { subtitle_id?: unknown }).subtitle_id || "")
        : undefined,
  });
  if (!realtimeSentiment) {
    return;
  }

  realtimeSentiments.value = [
    ...realtimeSentiments.value.slice(-9),
    realtimeSentiment,
  ];
}

function applyActionWindowPayload(raw: unknown) {
  const actionWindow = normalizeRuntimeActionWindow(raw);
  if (!actionWindow) {
    return;
  }

  runtimeActionWindows.value.push(actionWindow);
}

function buildFinalActionItems(finalActionsPayload: unknown): ActionItemDraft[] {
  return mergeActionItemCollections(runtimeActionWindows.value, finalActionsPayload);
}

function buildPipelineStartRequest(): PipelineStartRequest {
  const sessionId = config.value.meetingId.trim() || `session-${Date.now()}`;
  config.value.meetingId = sessionId;

  return {
    sessionId,
    inputDir: config.value.inputDir.trim() || undefined,
    globPattern: config.value.globPattern.trim() || "*.m4a",
    targetLang: normalizeTargetLanguage(config.value.targetLanguage),
    enableTranslation: config.value.translationEnabled,
    enableActions: config.value.actionEnabled,
    enableSentiment: config.value.sentimentEnabled,
  };
}

async function startMeeting() {
  try {
    if (isRunning.value || isFinalizing.value) {
      console.log(`[Meeting] Resetting previous meeting state before starting new one`);
      disconnect();
    }

    clearSubtitles();
    summary.value = null;
    summaryStatus.value = "idle";
    summaryError.value = null;
    sentimentStatus.value = "idle";
    liveError.value = null;
    isFinalizing.value = false;

    console.log(`[Meeting] Connecting to gateway...`);
    await api.meeting.connect();

    const request = buildPipelineStartRequest();
    isRunning.value = true;
    startTime.value = new Date().toISOString();
    duration.value = 0;
    runtimeInfoMessages.value = [];
    runtimeActionWindows.value = [];
    realtimeSentiments.value = [];
    sentimentStatus.value = config.value.sentimentEnabled ? "waiting" : "idle";

    if (durationTimer) {
      clearInterval(durationTimer);
    }
    durationTimer = setInterval(() => {
      duration.value++;
    }, 1000);

    api.meeting.onError((error) => {
      console.error("[Meeting] WebSocket error:", error);
      liveError.value = "网关连接异常，请检查 M5 服务（8000）是否正常。";
    });

    api.meeting.onClose(() => {
      if (isRunning.value || isFinalizing.value) {
        liveError.value = "网关连接已断开，请重新开始会议。";
        isRunning.value = false;
        isFinalizing.value = false;
      }
    });

    api.meeting.onMessage((message) => {
      const msg = message as {
        type: string;
        data?: unknown;
        message?: string;
      };

      if (msg.type === "info") {
        pushRuntimeInfoMessage(msg.message || "");
      } else if (msg.type === "subtitle") {
        const sub = msg.data as SubtitleEntry;
        subtitles.value.push(sub);
        liveError.value = null;
      } else if (msg.type === "asr_result") {
        applyAsrPayload(msg.data);
      } else if (msg.type === "translation") {
        applyTranslationPayload(msg.data);
      } else if (msg.type === "sentiment") {
        applySentimentPayload(msg.data);
      } else if (msg.type === "analysis_result") {
        const payload = extractAnalysisResultPayloads(msg.data);
        if (payload.translationPayload) {
          applyTranslationPayload(payload.translationPayload);
        }
        if (payload.sentimentPayload) {
          applyRealtimeSentimentPayload(payload.sentimentPayload, msg.data);
        }
      } else if (msg.type === "action_result") {
        applyActionWindowPayload(msg.data);
      } else if (msg.type === "stream_complete") {
        console.log(`[Meeting] Stream complete`);
      } else if (msg.type === "meeting_end_report") {
        const reportData = msg.data as {
          summary: { summary?: string; structured?: Record<string, unknown> };
          actions: {
            parsed_actions?: Array<{
              task: string;
              assignee?: string;
              deadline?: string;
            }>;
            action_items?:
              | string
              | Array<{ task: string; assignee?: string; deadline?: string }>;
          };
          sentiment?: unknown;
        };

        const summaryText = reportData.summary.summary || "";
        const keyPoints = deriveKeyPoints(
          summaryText,
          reportData.summary.structured,
        );
        const actionItems = buildFinalActionItems(reportData.actions);

        summary.value = {
          id: config.value.meetingId,
          meetingId: config.value.meetingId,
          title: "会议总结",
          summary: summaryText,
          keyPoints,
          actionItems: actionItems.map((item, i) => ({
            id: `action_${i}`,
            task: item.task,
            assignee: item.assignee,
            dueDate: item.dueDate,
            priority: "medium" as const,
            status: "pending" as const,
          })),
          participants: Array.from(
            new Set(subtitles.value.map((s) => s.speaker)),
          ),
          duration: duration.value,
          generatedAt: new Date().toISOString(),
        };
        isRunning.value = false;
        isFinalizing.value = false;
        summaryStatus.value = "ready";
        summaryError.value = null;

        if (config.value.sentimentEnabled) {
          applySentimentPayload(reportData.sentiment);
        }

        console.log(`[Meeting] End report received`);
      } else if (msg.type === "error") {
        const errData = msg.data as { message?: string } | undefined;
        const errorMessage = msg.message || errData?.message || "实时处理异常";
        console.error(`[Meeting] Error: ${errorMessage}`);
        liveError.value = errorMessage;
        if (summaryStatus.value === "loading" || isFinalizing.value) {
          isRunning.value = false;
          isFinalizing.value = false;
          summaryStatus.value = "error";
          summaryError.value = errorMessage || "会议总结生成失败";
        }
      }
    });

    api.meeting.start(request);
  } catch (error) {
    console.error("Failed to start meeting:", error);
    liveError.value = "无法连接网关，请确认服务是否启动。";
    isRunning.value = false;
    isFinalizing.value = false;
  }
}

async function endMeeting() {
  try {
    if (!isRunning.value || isFinalizing.value) {
      return;
    }

    summaryStatus.value = "loading";
    summaryError.value = null;
    liveError.value = null;
    isFinalizing.value = true;
    pushRuntimeInfoMessage("正在基于已输出内容生成会议总结...");
    api.meeting.end();

    if (durationTimer) {
      clearInterval(durationTimer);
      durationTimer = null;
    }
  } catch (error) {
    console.error("Failed to end meeting:", error);
  }
}

function disconnect() {
  if (durationTimer) {
    clearInterval(durationTimer);
    durationTimer = null;
  }
  api.meeting.disconnect();
  isRunning.value = false;
  isFinalizing.value = false;
  startTime.value = null;
}

function updateConfig(newConfig: Partial<MeetingConfig>) {
  const merged = { ...config.value, ...newConfig };
  merged.language = normalizeTargetLanguage(merged.language);
  merged.targetLanguage = normalizeTargetLanguage(merged.targetLanguage);
  config.value = merged;
}

function clearSubtitles() {
  subtitles.value = [];
  currentSentiment.value = null;
  liveError.value = null;
  runtimeInfoMessages.value = [];
  runtimeActionWindows.value = [];
  realtimeSentiments.value = [];
}

export function useMeetingStore() {
  return {
    isRunning,
    isFinalizing,
    startTime,
    duration,
    formattedDuration,
    participantCount,
    config,
    subtitles,
    runtimeInfoMessages,
    runtimeActionWindows,
    realtimeSentiments,
    currentSentiment,
    sentimentStatus,
    liveError,
    summary,
    summaryStatus,
    summaryError,
    startMeeting,
    endMeeting,
    disconnect,
    updateConfig,
    clearSubtitles,
  };
}
