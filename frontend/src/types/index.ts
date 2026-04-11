export interface MeetingConfig {
  meetingId: string;
  language: string;
  translationEnabled: boolean;
  targetLanguage: string;
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
