import { describe, expect, test } from "vitest";
import {
  buildActionItems,
  deriveKeyPoints,
  extractAnalysisResultPayloads,
  isTargetLanguageLocked,
  normalizeRealtimeSentimentEntry,
  normalizeSentimentReport,
  normalizeTargetLanguage,
  resolveSubtitleTranslationDisplay,
} from "./meetingMessageUtils";

describe("normalizeTargetLanguage", () => {
  test("maps BCP-47 codes to short target language codes", () => {
    expect(normalizeTargetLanguage("ja-JP")).toBe("ja");
    expect(normalizeTargetLanguage("en-US")).toBe("en");
    expect(normalizeTargetLanguage("zh-CN")).toBe("zh");
  });

  test("keeps short codes and falls back to english", () => {
    expect(normalizeTargetLanguage("ja")).toBe("ja");
    expect(normalizeTargetLanguage("unknown")).toBe("en");
    expect(normalizeTargetLanguage(undefined)).toBe("en");
  });
});

describe("normalizeSentimentReport", () => {
  test("normalizes a valid M4 sentiment report payload", () => {
    const payload = {
      overall_summary: {
        total_turns: 4,
        dominant_signals: [
          ["agreement", 3],
          ["hesitation", 1],
        ],
        atmosphere: "Positive/Constructive",
      },
      speaker_profiles: {
        Alice: {
          participation_count: 2,
          top_emotion: "开心语调",
          primary_behavior: "agreement",
          interruption_count: 0,
        },
      },
      significant_moments: [
        {
          timestamp: [12.3, 16.8],
          speaker: "Alice",
          reason: ["urgency", "interruption"],
          snippet: "我们必须在今天下班前完成。",
        },
      ],
    };

    expect(normalizeSentimentReport(payload)).toEqual({
      overall_summary: {
        total_turns: 4,
        dominant_signals: ["agreement", "hesitation"],
        atmosphere: "Positive/Constructive",
      },
      speaker_profiles: {
        Alice: {
          participation_count: 2,
          top_emotion: "开心语调",
          primary_behavior: "agreement",
          interruption_count: 0,
        },
      },
      significant_moments: [
        {
          timestamp: [12.3, 16.8],
          speaker: "Alice",
          reason: ["urgency", "interruption"],
          snippet: "我们必须在今天下班前完成。",
        },
      ],
    });
  });

  test("supports response wrapped by gateway status envelope", () => {
    const payload = {
      status: "success",
      result: {
        overall_summary: {
          total_turns: "3",
          dominant_signals: ["agreement", "neutral"],
          atmosphere: "Critical/Tense",
        },
        speaker_profiles: {},
        significant_moments: [],
      },
    };

    expect(normalizeSentimentReport(payload)).toEqual({
      overall_summary: {
        total_turns: 3,
        dominant_signals: ["agreement", "neutral"],
        atmosphere: "Critical/Tense",
      },
      speaker_profiles: {},
      significant_moments: [],
    });
  });

  test("returns null for invalid payload", () => {
    expect(normalizeSentimentReport({ overall_summary: {} })).toBeNull();
    expect(normalizeSentimentReport(null)).toBeNull();
  });
});

describe("buildActionItems", () => {
  test("prefers parsed_actions if available", () => {
    const input = {
      parsed_actions: [
        { task: "准备演示材料", assignee: "王五", deadline: "明天" },
      ],
      action_items: "- 李四: 这条不应被采用",
    };

    expect(buildActionItems(input)).toEqual([
      { task: "准备演示材料", assignee: "王五", deadline: "明天" },
    ]);
  });

  test("falls back to parsing action_items markdown text", () => {
    const input = {
      action_items: "- 张三: 完成项目文档 (周五前)\n- 安排评审会议",
    };

    expect(buildActionItems(input)).toEqual([
      { task: "完成项目文档", assignee: "张三", deadline: "周五前" },
      { task: "安排评审会议", assignee: undefined, deadline: undefined },
    ]);
  });
});

describe("deriveKeyPoints", () => {
  test("uses structured key_points first", () => {
    const structured = {
      key_points: ["要点一", "要点二"],
    };

    expect(deriveKeyPoints("摘要文本", structured)).toEqual([
      "要点一",
      "要点二",
    ]);
  });

  test("falls back to sentence split when structured key_points missing", () => {
    const text = "第一点说明。第二点说明。第三点说明。";
    expect(deriveKeyPoints(text, {})).toEqual([
      "第一点说明",
      "第二点说明",
      "第三点说明",
    ]);
  });
});

describe("extractAnalysisResultPayloads", () => {
  test("extracts nested sentiment and translation payloads", () => {
    const data = {
      sentiment: { analysis: { sentiment: "positive" } },
      translation: { translated_text: "こんにちは" },
    };

    expect(extractAnalysisResultPayloads(data)).toEqual({
      sentimentPayload: { analysis: { sentiment: "positive" } },
      translationPayload: { translated_text: "こんにちは" },
    });
  });

  test("returns empty object for invalid input", () => {
    expect(extractAnalysisResultPayloads(null)).toEqual({});
  });
});

describe("normalizeRealtimeSentimentEntry", () => {
  test("normalizes realtime sentiment payloads from the gateway", () => {
    const payload = {
      status: "success",
      speaker: "Alice",
      label: "positive",
      signal: "agreement",
      explanation: "检测到 agreement 信号，整体语气偏 positive。",
    };

    expect(
      normalizeRealtimeSentimentEntry(payload, {
        subtitleId: "subtitle-1",
        timestamp: 12.4,
      }),
    ).toEqual({
      id: "subtitle-1",
      speaker: "Alice",
      label: "positive",
      signal: "agreement",
      explanation: "检测到 agreement 信号，整体语气偏 positive。",
      timestamp: 12.4,
    });
  });

  test("returns null when realtime payload has no usable label", () => {
    expect(normalizeRealtimeSentimentEntry({ foo: "bar" })).toBeNull();
  });
});

describe("resolveSubtitleTranslationDisplay", () => {
  test("returns translated text when translation is available", () => {
    expect(resolveSubtitleTranslationDisplay(true, "Hello world")).toEqual({
      text: "Hello world",
      pending: false,
    });
  });

  test("returns pending placeholder when translation is missing", () => {
    expect(resolveSubtitleTranslationDisplay(true, undefined)).toEqual({
      text: "翻译中...",
      pending: true,
    });
  });

  test("returns null when translation is disabled", () => {
    expect(resolveSubtitleTranslationDisplay(false, "Hello world")).toEqual({
      text: null,
      pending: false,
    });
  });
});

describe("isTargetLanguageLocked", () => {
  test("locks target language when meeting is running", () => {
    expect(isTargetLanguageLocked(true)).toBe(true);
  });

  test("unlocks target language when meeting is not running", () => {
    expect(isTargetLanguageLocked(false)).toBe(false);
  });
});
