import { ref, computed } from "vue";
import type {
  MeetingConfig,
  SubtitleEntry,
  SentimentData,
  SentimentTrendPoint,
  MeetingSummary,
} from "../types";
import { api } from "../services/api";
import {
  buildActionItems,
  deriveKeyPoints,
  extractAnalysisResultPayloads,
  extractSentimentLabel,
  normalizeTargetLanguage,
  shouldMarkSentimentStalled,
} from "./meetingMessageUtils";

type SummaryStatus = "idle" | "loading" | "ready" | "error";
type SentimentStatus = "idle" | "waiting" | "active" | "stalled";

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
const sentimentTrend = ref<SentimentTrendPoint[]>([]);
const summaryStatus = ref<SummaryStatus>("idle");
const summaryError = ref<string | null>(null);
const sentimentStatus = ref<SentimentStatus>("idle");
const sentimentMessageCount = ref(0);

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
  const label = extractSentimentLabel(raw);
  const pos = label === "positive" ? 0.7 : 0.1;
  const neg = label === "negative" ? 0.7 : 0.1;
  const neu = label === "neutral" ? 0.7 : 0.2;
  const overall = label === "positive" ? 0.75 : label === "negative" ? 0.25 : 0.5;

  sentimentMessageCount.value += 1;
  sentimentStatus.value = "active";

  sentimentTrend.value.push({
    time: new Date().toISOString(),
    value: overall,
  });
  if (sentimentTrend.value.length > 30) {
    sentimentTrend.value = sentimentTrend.value.slice(-30);
  }

  currentSentiment.value = {
    overall,
    positive: pos,
    negative: neg,
    neutral: neu,
    engagement: 0.6,
    trend: [...sentimentTrend.value],
  };
}

function updateSentimentWaitingState() {
  if (
    sentimentStatus.value !== "active" &&
    shouldMarkSentimentStalled(subtitles.value.length, sentimentMessageCount.value)
  ) {
    sentimentStatus.value = "stalled";
  }
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

    console.log(`[Meeting] Connecting to gateway...`);
    await api.meeting.connect();

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
        sentimentStatus.value = config.value.sentimentEnabled ? "waiting" : "idle";
        sentimentMessageCount.value = 0;

        durationTimer = setInterval(() => {
          duration.value++;
        }, 1000);
        console.log(`[Meeting] Started: ${config.value.meetingId}`);
      } else if (msg.type === "subtitle") {
        const sub = msg.data as SubtitleEntry;
        subtitles.value.push(sub);
        if (subtitles.value.length > 50) {
          subtitles.value = subtitles.value.slice(-50);
        }
        updateSentimentWaitingState();
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
        updateSentimentWaitingState();
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
        console.log(`[Meeting] End report received`);
      } else if (msg.type === "error") {
        const errData = msg.data as { message?: string };
        console.error(`[Meeting] Error: ${errData.message}`);
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
    );
  } catch (error) {
    console.error("Failed to start meeting:", error);
  }
}

async function endMeeting() {
  try {
    summary.value = null;
    summaryStatus.value = "loading";
    summaryError.value = null;
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
  sentimentTrend.value = [];
  currentSentiment.value = null;
  sentimentMessageCount.value = 0;
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
