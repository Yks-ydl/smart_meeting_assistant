import { ref, computed } from "vue";
import type {
  MeetingConfig,
  SubtitleEntry,
  SentimentData,
  MeetingSummary,
} from "../types";
import { api } from "../services/api";
import {
  buildActionItems,
  deriveKeyPoints,
  extractAnalysisResultPayloads,
  normalizeSentimentReport,
  normalizeTargetLanguage,
} from "./meetingMessageUtils";

type SummaryStatus = "idle" | "loading" | "ready" | "error";
type SentimentStatus = "idle" | "waiting" | "ready" | "error";

const isRunning = ref(false);
const startTime = ref<string | null>(null);
const duration = ref(0);
const config = ref<MeetingConfig>({
  meetingId: "",
  language: "zh",
  translationEnabled: true,
  targetLanguage: "en",
  sentimentEnabled: true,
});

const subtitles = ref<SubtitleEntry[]>([]);
const currentSentiment = ref<SentimentData | null>(null);
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

function applyTranslationPayload(raw: unknown) {
  const transData = raw as { subtitle_id?: string; translated_text?: string };
  if (!transData?.translated_text || subtitles.value.length === 0) {
    return;
  }

  if (transData.subtitle_id) {
    const targetIndex = subtitles.value.findIndex(
      (sub) => sub.id === transData.subtitle_id,
    );
    if (targetIndex >= 0) {
      subtitles.value[targetIndex].translation = transData.translated_text;
      return;
    }
  }

  const lastSub = subtitles.value[subtitles.value.length - 1];
  lastSub.translation = transData.translated_text;
}

function applySentimentPayload(raw: unknown) {
  const report = normalizeSentimentReport(raw);
  if (!report) {
    sentimentStatus.value = "error";
    return;
  }

  currentSentiment.value = report;
  sentimentStatus.value = "ready";
}

async function startMeeting(
  mode: "demo" | "realtime" = "demo",
  inputDir?: string,
) {
  try {
    if (isRunning.value) {
      console.log(`[Meeting] Ending previous meeting before starting new one`);
      await endMeeting();
    }
    disconnect();

    clearSubtitles();
    summary.value = null;
    summaryStatus.value = "idle";
    summaryError.value = null;
    sentimentStatus.value = "idle";
    liveError.value = null;

    console.log(`[Meeting] Connecting to gateway...`);
    await api.meeting.connect();

    api.meeting.onError((error) => {
      console.error("[Meeting] WebSocket error:", error);
      liveError.value = "网关连接异常，请检查 M5 服务（8000）是否正常。";
    });

    api.meeting.onClose(() => {
      if (isRunning.value) {
        liveError.value = "网关连接已断开，请重新开始会议。";
      }
    });

    api.meeting.onMessage((message) => {
      const msg = message as { type: string; data: unknown };

      if (msg.type === "meeting_started") {
        const data = msg.data as {
          session_id?: string;
          meeting_id?: string;
          mode?: string;
          start_time?: string;
        };
        isRunning.value = true;
        startTime.value = data.start_time || new Date().toISOString();
        config.value.meetingId = data.meeting_id || data.session_id || "";
        duration.value = 0;
        summaryStatus.value = "idle";
        summaryError.value = null;
        sentimentStatus.value = config.value.sentimentEnabled
          ? "waiting"
          : "idle";
        liveError.value = null;

        durationTimer = setInterval(() => {
          duration.value++;
        }, 1000);
        console.log(`[Meeting] Started: ${config.value.meetingId}`);
      } else if (msg.type === "subtitle") {
        const sub = msg.data as SubtitleEntry;
        subtitles.value.push(sub);
        liveError.value = null;
        if (subtitles.value.length > 50) {
          subtitles.value = subtitles.value.slice(-50);
        }
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
          applySentimentPayload(payload.sentimentPayload);
        }
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
        const actionItems = buildActionItems(reportData.actions);

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
            dueDate: item.deadline,
            priority: "medium" as const,
            status: "pending" as const,
          })),
          participants: Array.from(
            new Set(subtitles.value.map((s) => s.speaker)),
          ),
          duration: duration.value,
          generatedAt: new Date().toISOString(),
        };
        summaryStatus.value = "ready";
        summaryError.value = null;

        if (config.value.sentimentEnabled) {
          applySentimentPayload(reportData.sentiment);
        }

        console.log(`[Meeting] End report received`);
      } else if (msg.type === "error") {
        const errData = msg.data as { message?: string };
        console.error(`[Meeting] Error: ${errData.message}`);
        liveError.value = errData.message || "实时处理异常";
        if (summaryStatus.value === "loading") {
          summaryStatus.value = "error";
          summaryError.value = errData.message || "会议总结生成失败";
        }
      }
    });

    api.meeting.start(
      mode,
      inputDir,
      normalizeTargetLanguage(config.value.targetLanguage),
      config.value.sentimentEnabled,
    );
  } catch (error) {
    console.error("Failed to start meeting:", error);
    liveError.value = "无法连接网关，请确认服务是否启动。";
  }
}

async function endMeeting() {
  try {
    summary.value = null;
    summaryStatus.value = "loading";
    summaryError.value = null;
    liveError.value = null;
    api.meeting.end();

    isRunning.value = false;
    startTime.value = null;

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
}

export function useMeetingStore() {
  return {
    isRunning,
    startTime,
    duration,
    formattedDuration,
    participantCount,
    config,
    subtitles,
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
