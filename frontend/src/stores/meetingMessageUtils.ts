export type ShortLanguageCode = "zh" | "en" | "ja";

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

export function extractSentimentLabel(
  payload: unknown,
): "positive" | "neutral" | "negative" {
  if (!isObject(payload)) {
    return "neutral";
  }

  const nested = isObject(payload.analysis)
    ? toCleanString(payload.analysis.sentiment)
    : "";
  const flat = toCleanString(payload.sentiment);
  const label = (nested || flat).toLowerCase();

  if (label === "positive" || label === "negative" || label === "neutral") {
    return label;
  }

  return "neutral";
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

export function shouldMarkSentimentStalled(
  subtitleCount: number,
  sentimentMessageCount: number,
  threshold: number = 6,
): boolean {
  return subtitleCount >= threshold && sentimentMessageCount === 0;
}

export function extractAnalysisResultPayloads(data: unknown): {
  sentimentPayload?: Record<string, unknown>;
  translationPayload?: Record<string, unknown>;
} {
  if (!isObject(data)) {
    return {};
  }

  const sentimentPayload = isObject(data.sentiment)
    ? data.sentiment
    : undefined;
  const translationPayload = isObject(data.translation)
    ? data.translation
    : undefined;

  return {
    sentimentPayload,
    translationPayload,
  };
}
