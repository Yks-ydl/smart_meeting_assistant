export interface MeetingConfig {
  meetingId: string;
  inputDir: string;
  globPattern: string;
  language: string;
  translationEnabled: boolean;
  targetLanguage: string;
  actionEnabled: boolean;
  sentimentEnabled: boolean;
}

export interface MeetingStatus {
  isRunning: boolean;
  startTime?: string;
  duration: number;
  participantCount: number;
}

export interface SubtitleEntry {
  id: string;
  speaker: string;
  text: string;
  translation?: string;
  timestamp: string;
  language: string;
  startTime?: number;
  endTime?: number;
  source?: string;
}

export interface PipelineStartRequest {
  sessionId: string;
  inputDir?: string;
  globPattern: string;
  targetLang: "zh" | "en" | "ja";
  enableTranslation: boolean;
  enableActions: boolean;
  enableSentiment: boolean;
}

export interface RuntimeInfoEntry {
  id: string;
  message: string;
  createdAt: string;
}

export interface ActionItemDraft {
  task: string;
  assignee?: string;
  dueDate?: string;
}

export interface RuntimeActionWindow {
  id: string;
  windowStart: number;
  windowEnd: number;
  items: ActionItemDraft[];
}

export interface RealtimeSentimentEntry {
  id: string;
  speaker: string;
  label: string;
  signal?: string;
  explanation?: string;
  timestamp?: number;
}

export interface SentimentData {
  overall_summary: SentimentOverallSummary;
  speaker_profiles: Record<string, SentimentSpeakerProfile>;
  significant_moments: SentimentSignificantMoment[];
}

export interface SentimentOverallSummary {
  total_turns: number;
  dominant_signals: string[];
  atmosphere: string;
}

export interface SentimentSpeakerProfile {
  participation_count: number;
  top_emotion: string;
  primary_behavior: string;
  interruption_count: number;
}

export interface SentimentSignificantMoment {
  timestamp: [number, number] | string;
  speaker: string;
  reason: string[];
  snippet: string;
}

export interface ActionItem {
  id: string;
  task: string;
  assignee?: string;
  dueDate?: string;
  priority: "high" | "medium" | "low";
  status: "pending" | "in_progress" | "completed";
}

export interface MeetingSummary {
  id: string;
  meetingId: string;
  title: string;
  summary: string;
  keyPoints: string[];
  actionItems: ActionItem[];
  participants: string[];
  duration: number;
  generatedAt: string;
}

export interface TranslateRequest {
  text: string;
  sourceLanguage: string;
  targetLanguage: string;
}

export interface TranslateResponse {
  originalText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
}

export interface ActionItemsRequest {
  text: string;
}

export interface ActionItemsResponse {
  actionItems: ActionItem[];
}
