export interface MeetingConfig {
  meetingId: string
  language: string
  translationEnabled: boolean
  targetLanguage: string
  sentimentEnabled: boolean
}

export interface MeetingStatus {
  isRunning: boolean
  startTime?: string
  duration: number
  participantCount: number
}

export interface SubtitleEntry {
  id: string
  speaker: string
  text: string
  translation?: string
  timestamp: string
  language: string
}

export interface SentimentData {
  overall: number
  positive: number
  negative: number
  neutral: number
  engagement: number
  trend: SentimentTrendPoint[]
}

export interface SentimentTrendPoint {
  time: string
  value: number
}

export interface ActionItem {
  id: string
  task: string
  assignee?: string
  dueDate?: string
  priority: 'high' | 'medium' | 'low'
  status: 'pending' | 'in_progress' | 'completed'
}

export interface MeetingSummary {
  id: string
  meetingId: string
  title: string
  summary: string
  keyPoints: string[]
  actionItems: ActionItem[]
  participants: string[]
  duration: number
  generatedAt: string
}

export interface TranslateRequest {
  text: string
  sourceLanguage: string
  targetLanguage: string
}

export interface TranslateResponse {
  originalText: string
  translatedText: string
  sourceLanguage: string
  targetLanguage: string
}

export interface SentimentRequest {
  text: string
}

export interface SentimentResponse {
  sentiment: 'positive' | 'negative' | 'neutral'
  score: number
  confidence: number
}

export interface ActionItemsRequest {
  text: string
}

export interface ActionItemsResponse {
  actionItems: ActionItem[]
}
