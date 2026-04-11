import { http, HttpResponse, delay } from 'msw'
import type {
  MeetingConfig,
  MeetingSummary,
  TranslateRequest,
  TranslateResponse,
  SentimentRequest,
  SentimentResponse,
  ActionItemsRequest,
  ActionItemsResponse,
} from '../types'

const API_BASE = '/api/v1'

let meetingState = {
  isRunning: false,
  startTime: null as string | null,
  config: null as MeetingConfig | null,
}

export const handlers = [
  http.post(`${API_BASE}/meeting/start`, async () => {
    await delay(300)
    meetingState.isRunning = true
    meetingState.startTime = new Date().toISOString()
    return HttpResponse.json({
      success: true,
      data: {
        meetingId: 'meeting-' + Date.now(),
        status: 'started',
        startTime: meetingState.startTime,
      },
    })
  }),

  http.post(`${API_BASE}/meeting/end`, async () => {
    await delay(300)
    meetingState.isRunning = false
    const duration = meetingState.startTime
      ? Date.now() - new Date(meetingState.startTime).getTime()
      : 0
    meetingState.startTime = null
    return HttpResponse.json({
      success: true,
      data: {
        status: 'ended',
        duration: Math.floor(duration / 1000),
      },
    })
  }),

  http.put(`${API_BASE}/meeting/config`, async ({ request }) => {
    await delay(200)
    const config = (await request.json()) as MeetingConfig
    meetingState.config = config
    return HttpResponse.json({
      success: true,
      data: config,
    })
  }),

  http.get(`${API_BASE}/meeting/status`, async () => {
    await delay(100)
    return HttpResponse.json({
      success: true,
      data: {
        isRunning: meetingState.isRunning,
        startTime: meetingState.startTime,
        duration: meetingState.startTime
          ? Math.floor((Date.now() - new Date(meetingState.startTime).getTime()) / 1000)
          : 0,
        participantCount: 3,
      },
    })
  }),

  http.get(`${API_BASE}/meeting/summary`, async () => {
    await delay(500)
    const summary: MeetingSummary = {
      id: 'summary-' + Date.now(),
      meetingId: 'meeting-demo',
      title: '产品开发周会',
      summary:
        '本次会议讨论了新功能的开发进度、用户反馈分析以及下一阶段的开发计划。团队决定优先处理用户反馈中的关键问题，并计划在两周内完成主要功能的优化。',
      keyPoints: [
        '新用户界面设计已完成80%，预计下周完成剩余部分',
        '用户反馈显示搜索功能需要优化，已列入优先开发计划',
        '性能优化已完成初步测试，响应时间提升30%',
        '下阶段将重点开发移动端适配功能',
      ],
      actionItems: [
        {
          id: 'action-1',
          task: '完成用户界面设计剩余部分',
          assignee: '张三',
          dueDate: '2024-01-15',
          priority: 'high',
          status: 'pending',
        },
        {
          id: 'action-2',
          task: '优化搜索功能性能',
          assignee: '李四',
          dueDate: '2024-01-18',
          priority: 'high',
          status: 'pending',
        },
        {
          id: 'action-3',
          task: '编写移动端适配技术方案',
          assignee: '王五',
          dueDate: '2024-01-20',
          priority: 'medium',
          status: 'pending',
        },
      ],
      participants: ['张三', '李四', '王五', '赵六'],
      duration: 3600,
      generatedAt: new Date().toISOString(),
    }
    return HttpResponse.json({
      success: true,
      data: summary,
    })
  }),

  http.post(`${API_BASE}/ai/summarize`, async ({ request }) => {
    await delay(800)
    const body = (await request.json()) as { text: string }
    return HttpResponse.json({
      success: true,
      data: {
        summary: '这是对提供内容的智能摘要：' + body.text.substring(0, 100) + '...',
        keyPoints: ['要点1：讨论了项目进度', '要点2：确定了下一步计划', '要点3：分配了任务'],
      },
    })
  }),

  http.post(`${API_BASE}/ai/translate`, async ({ request }) => {
    await delay(300)
    const body = (await request.json()) as TranslateRequest
    const response: TranslateResponse = {
      originalText: body.text,
      translatedText: `[翻译结果] ${body.text}`,
      sourceLanguage: body.sourceLanguage,
      targetLanguage: body.targetLanguage,
    }
    return HttpResponse.json({
      success: true,
      data: response,
    })
  }),

  http.post(`${API_BASE}/ai/sentiment`, async ({ request }) => {
    await delay(200)
    const body = (await request.json()) as SentimentRequest
    const positiveWords = ['好', '棒', '成功', '完成', '优秀', '满意', '高兴', 'good', 'great', 'excellent']
    const negativeWords = ['问题', '失败', '困难', '糟糕', '不满', 'bad', 'problem', 'fail']

    let score = 0.5
    const text = body.text.toLowerCase()

    positiveWords.forEach((word) => {
      if (text.includes(word)) score += 0.1
    })
    negativeWords.forEach((word) => {
      if (text.includes(word)) score -= 0.1
    })

    score = Math.max(0, Math.min(1, score))

    const response: SentimentResponse = {
      sentiment: score > 0.6 ? 'positive' : score < 0.4 ? 'negative' : 'neutral',
      score,
      confidence: 0.85 + Math.random() * 0.1,
    }
    return HttpResponse.json({
      success: true,
      data: response,
    })
  }),

  http.post(`${API_BASE}/ai/action-items`, async ({ request }) => {
    await delay(400)
    const body = (await request.json()) as ActionItemsRequest
    const response: ActionItemsResponse = {
      actionItems: [
        {
          id: 'extracted-action-1',
          task: '跟进会议中提到的问题',
          priority: 'medium',
          status: 'pending',
        },
        {
          id: 'extracted-action-2',
          task: '准备下一阶段的工作计划',
          priority: 'high',
          status: 'pending',
        },
      ],
    }
    return HttpResponse.json({
      success: true,
      data: response,
    })
  }),
]
