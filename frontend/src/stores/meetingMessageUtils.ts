export type ShortLanguageCode = "zh" | "en" | "ja";

import type {
  ActionItemDraft,
  RealtimeSentimentEntry,
  RuntimeActionWindow,
  SentimentData,
  SubtitleEntry,
} from "../types";

type ActionItemLike = {
  task: string;
  assignee?: string;
  deadline?: string;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toCleanString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function normalizeTargetLanguage(input?: string): ShortLanguageCode {
  if (!input) {
    return "en";
  }

  const normalized = input.toLowerCase();
  const head = normalized.split(/[-_]/)[0];
  if (head === "zh" || head === "en" || head === "ja") {
    return head;
  }

  return "en";
}

export function resolveSubtitleTranslationDisplay(
  translationEnabled: boolean,
  translation?: string,
): { text: string | null; pending: boolean } {
  if (!translationEnabled) {
    return { text: null, pending: false };
  }

  const normalizedText = toCleanString(translation);
  if (normalizedText) {
    return { text: normalizedText, pending: false };
  }

  return { text: "翻译中...", pending: true };
}

export function isTargetLanguageLocked(isMeetingRunning: boolean): boolean {
  return isMeetingRunning;
}

export function normalizePipelineSubtitle(
  value: unknown,
): SubtitleEntry | null {
  if (!isObject(value)) {
    return null;
  }

  const text = toCleanString(value.corrected_text) || toCleanString(value.text);
  const speaker = toCleanString(value.speaker) || toCleanString(value.speaker_label);
  const startTime = toFiniteNumber(value.start_time);
  const endTime = toFiniteNumber(value.end_time);
  const timestamp =
    toCleanString(value.timestamp) ||
    (startTime !== null ? startTime.toFixed(3) : "0.000");

  if (!text || !speaker) {
    return null;
  }

  return {
    id:
      toCleanString(value.id) ||
      `${speaker}-${timestamp}-${text.slice(0, 24)}`,
    speaker,
    text,
    timestamp,
    language: normalizeTargetLanguage(toCleanString(value.language) || "zh"),
    startTime: startTime ?? undefined,
    endTime: endTime ?? undefined,
    source: toCleanString(value.source) || undefined,
  };
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
}

function normalizeDominantSignals(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (typeof item === "string") {
        return item.trim();
      }

      if (Array.isArray(item) && item.length > 0) {
        return toCleanString(item[0]);
      }

      return "";
    })
    .filter((item) => item.length > 0);
}

function normalizeSpeakerProfiles(
  value: unknown,
): SentimentData["speaker_profiles"] {
  if (!isObject(value)) {
    return {};
  }

  const normalized: SentimentData["speaker_profiles"] = {};

  for (const [speaker, rawProfile] of Object.entries(value)) {
    if (!isObject(rawProfile)) {
      continue;
    }

    normalized[speaker] = {
      participation_count: Math.max(
        0,
        Math.floor(toFiniteNumber(rawProfile.participation_count) ?? 0),
      ),
      top_emotion: toCleanString(rawProfile.top_emotion) || "N/A",
      primary_behavior: toCleanString(rawProfile.primary_behavior) || "Neutral",
      interruption_count: Math.max(
        0,
        Math.floor(toFiniteNumber(rawProfile.interruption_count) ?? 0),
      ),
    };
  }

  return normalized;
}

function normalizeSignificantMoments(
  value: unknown,
): SentimentData["significant_moments"] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => {
      if (!isObject(item)) {
        return null;
      }

      let timestamp: [number, number] | string = "";
      if (Array.isArray(item.timestamp) && item.timestamp.length >= 2) {
        const start = toFiniteNumber(item.timestamp[0]);
        const end = toFiniteNumber(item.timestamp[1]);
        if (start !== null && end !== null) {
          timestamp = [start, end];
        }
      }
      if (!timestamp) {
        timestamp = toCleanString(item.timestamp) || "未知";
      }

      const reason = Array.isArray(item.reason)
        ? item.reason
            .map((entry) => toCleanString(entry))
            .filter((entry) => entry.length > 0)
        : [];

      return {
        timestamp,
        speaker: toCleanString(item.speaker) || "Unknown",
        reason,
        snippet: toCleanString(item.snippet),
      };
    })
    .filter(
      (item): item is SentimentData["significant_moments"][number] =>
        item !== null,
    );
}

function unwrapSentimentPayload(
  payload: unknown,
): Record<string, unknown> | null {
  if (!isObject(payload)) {
    return null;
  }

  if (isObject(payload.result)) {
    return payload.result;
  }

  if (isObject(payload.data) && isObject(payload.data.result)) {
    return payload.data.result;
  }

  if (isObject(payload.data) && isObject(payload.data.overall_summary)) {
    return payload.data;
  }

  if (isObject(payload.overall_summary)) {
    return payload;
  }

  return null;
}


function unwrapRealtimeSentimentPayload(
  payload: unknown,
): Record<string, unknown> | null {
  if (!isObject(payload)) {
    return null;
  }

  if (isObject(payload.result)) {
    return payload.result;
  }

  if (isObject(payload.data)) {
    return payload.data;
  }

  return payload;
}

export function normalizeSentimentReport(
  payload: unknown,
): SentimentData | null {
  const rawReport = unwrapSentimentPayload(payload);
  if (!rawReport || !isObject(rawReport.overall_summary)) {
    return null;
  }

  const totalTurns = toFiniteNumber(rawReport.overall_summary.total_turns);
  const atmosphere = toCleanString(rawReport.overall_summary.atmosphere);
  if (totalTurns === null || atmosphere.length === 0) {
    return null;
  }

  return {
    overall_summary: {
      total_turns: Math.max(0, Math.floor(totalTurns)),
      dominant_signals: normalizeDominantSignals(
        rawReport.overall_summary.dominant_signals,
      ),
      atmosphere,
    },
    speaker_profiles: normalizeSpeakerProfiles(rawReport.speaker_profiles),
    significant_moments: normalizeSignificantMoments(
      rawReport.significant_moments,
    ),
  };
}

export function normalizeRealtimeSentimentEntry(
  payload: unknown,
  context?: { speaker?: string; timestamp?: unknown; subtitleId?: string },
): RealtimeSentimentEntry | null {
  const rawPayload = unwrapRealtimeSentimentPayload(payload);
  if (!rawPayload) {
    return null;
  }

  const label =
    toCleanString(rawPayload.label) ||
    toCleanString(rawPayload.sentiment) ||
    toCleanString(rawPayload.text);
  if (!label) {
    return null;
  }

  const speaker =
    toCleanString(rawPayload.speaker) ||
    toCleanString(context?.speaker) ||
    "Unknown";
  const timestamp =
    toFiniteNumber(rawPayload.timestamp) ?? toFiniteNumber(context?.timestamp) ?? undefined;

  return {
    id:
      toCleanString(context?.subtitleId) ||
      `${speaker}-${label}-${timestamp ?? "na"}`,
    speaker,
    label,
    signal: toCleanString(rawPayload.signal) || undefined,
    explanation: toCleanString(rawPayload.explanation) || undefined,
    timestamp,
  };
}

function parseLineActionItem(line: string): ActionItemLike | null {
  const trimmed = line.trim();
  if (!trimmed) {
    return null;
  }

  let cleaned = trimmed
    .replace(/^[-*•]\s*/, "")
    .replace(/^\d+\.\s*/, "")
    .trim();

  if (!cleaned) {
    return null;
  }

  const lower = cleaned.toLowerCase();
  if (lower === "无" || lower === "无待办事项" || lower === "none") {
    return null;
  }

  let deadline: string | undefined;
  const deadlineMatch = cleaned.match(/[（(]([^（）()]+)[）)]\s*$/);
  if (deadlineMatch) {
    deadline = deadlineMatch[1].trim();
    cleaned = cleaned.slice(0, cleaned.length - deadlineMatch[0].length).trim();
  }

  let assignee: string | undefined;
  let task = cleaned;
  const assigneeMatch = cleaned.match(/^([^：:]+)[:：]\s*(.+)$/);
  if (assigneeMatch) {
    assignee = assigneeMatch[1].trim();
    task = assigneeMatch[2].trim();
  }

  if (!task) {
    return null;
  }

  return { task, assignee, deadline };
}

function normalizeActionList(list: unknown): ActionItemLike[] {
  if (!Array.isArray(list)) {
    return [];
  }

  const normalized: ActionItemLike[] = [];
  for (const item of list) {
    if (!isObject(item)) {
      continue;
    }

    const task = toCleanString(item.task);
    if (!task) {
      continue;
    }

    const assignee = toCleanString(item.assignee) || undefined;
    const deadline = toCleanString(item.deadline) || undefined;
    normalized.push({ task, assignee, deadline });
  }

  return normalized;
}

function toActionItemDraft(item: ActionItemLike): ActionItemDraft {
  return {
    task: item.task,
    assignee: item.assignee,
    dueDate: item.deadline,
  };
}

function buildActionItemKey(item: ActionItemLike | ActionItemDraft): string {
  const dueDate = "dueDate" in item
    ? item.dueDate
    : "deadline" in item
      ? item.deadline
      : undefined;

  return [
    toCleanString(item.task).toLowerCase(),
    toCleanString(item.assignee).toLowerCase(),
    toCleanString(dueDate).toLowerCase(),
  ].join("|");
}

export function buildActionItems(actions: unknown): ActionItemLike[] {
  if (!isObject(actions)) {
    return [];
  }

  const parsedActions = normalizeActionList(actions.parsed_actions);
  if (parsedActions.length > 0) {
    return parsedActions;
  }

  const structuredActionItems = normalizeActionList(actions.action_items);
  if (structuredActionItems.length > 0) {
    return structuredActionItems;
  }

  const actionText = toCleanString(actions.action_items);
  if (!actionText) {
    return [];
  }

  return actionText
    .split("\n")
    .map((line) => parseLineActionItem(line))
    .filter((item): item is ActionItemLike => item !== null);
}

export function normalizeRuntimeActionWindow(
  payload: unknown,
): RuntimeActionWindow | null {
  if (!isObject(payload)) {
    return null;
  }

  const windowStart = toFiniteNumber(payload.window_start);
  const windowEnd = toFiniteNumber(payload.window_end);
  const items = buildActionItems(payload.actions).map(toActionItemDraft);

  if (windowStart === null || windowEnd === null || items.length === 0) {
    return null;
  }

  return {
    id: `${windowStart.toFixed(3)}-${windowEnd.toFixed(3)}-${items.length}`,
    windowStart,
    windowEnd,
    items,
  };
}

export function mergeActionItemCollections(
  runtimeWindows: RuntimeActionWindow[],
  finalActions: unknown,
): ActionItemDraft[] {
  const merged = [
    ...runtimeWindows.flatMap((window) => window.items),
    ...buildActionItems(finalActions).map(toActionItemDraft),
  ];

  const seen = new Set<string>();
  return merged.filter((item) => {
    const key = buildActionItemKey(item);
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function deriveKeyPoints(
  summaryText?: string,
  structured?: Record<string, unknown>,
): string[] {
  const structuredPoints = Array.isArray(structured?.key_points)
    ? structured.key_points
        .map((point) => toCleanString(point))
        .filter((point) => point.length > 0)
    : [];

  if (structuredPoints.length > 0) {
    return structuredPoints;
  }

  const text = toCleanString(summaryText);
  if (!text) {
    return [];
  }

  return text
    .split(/[。！？.!?]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .slice(0, 5);
}

export function extractAnalysisResultPayloads(data: unknown): {
  sentimentPayload?: Record<string, unknown>;
  translationPayload?: Record<string, unknown>;
} {
  if (!isObject(data)) {
    return {};
  }

  const subtitleId = toCleanString(data.subtitle_id);

  const sentimentPayload = isObject(data.sentiment)
    ? data.sentiment
    : undefined;
  const translationPayload = isObject(data.translation)
    ? {
        ...(subtitleId && !toCleanString(data.translation.subtitle_id)
          ? { subtitle_id: subtitleId }
          : {}),
        ...data.translation,
      }
    : undefined;

  return {
    sentimentPayload,
    translationPayload,
  };
}
