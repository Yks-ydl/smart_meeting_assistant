import { describe, expect, test } from "vitest";
import {
  buildActionItems,
  deriveKeyPoints,
  extractAnalysisResultPayloads,
  extractSentimentLabel,
  isTargetLanguageLocked,
  normalizeTargetLanguage,
  resolveSubtitleTranslationDisplay,
  shouldMarkSentimentStalled,
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

describe("extractSentimentLabel", () => {
  test("reads nested analysis payload", () => {
    const payload = {
      status: "success",
      analysis: {
        sentiment: "negative",
      },
    };
    expect(extractSentimentLabel(payload)).toBe("negative");
  });

  test("reads flat payload", () => {
    const payload = { sentiment: "positive" };
    expect(extractSentimentLabel(payload)).toBe("positive");
  });

  test("falls back to neutral for unknown values", () => {
    const payload = { analysis: { sentiment: "mixed" } };
    expect(extractSentimentLabel(payload)).toBe("neutral");
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

describe("shouldMarkSentimentStalled", () => {
  test("marks stalled when enough subtitles arrived with zero sentiment messages", () => {
    expect(shouldMarkSentimentStalled(6, 0)).toBe(true);
  });

  test("does not mark stalled when sentiment messages exist", () => {
    expect(shouldMarkSentimentStalled(10, 1)).toBe(false);
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
