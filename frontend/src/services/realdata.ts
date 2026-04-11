import type { SubtitleEntry, SentimentData, SentimentTrendPoint } from '../types'

type MessageHandler = (data: unknown) => void
type ConnectionHandler = () => void

/**
 * 真实数据 WebSocket 服务
 * 通过 SSE (Server-Sent Events) 从后端获取 VCSum 数据集的真实字幕
 * 替代原有的 MockWebSocketService
 */
class RealDataService {
  private eventSource: EventSource | null = null
  private messageHandlers: MessageHandler[] = []
  private openHandlers: ConnectionHandler[] = []
  private closeHandlers: ConnectionHandler[] = []
  private errorHandlers: ((error: unknown) => void)[] = []
  private isConnected = false
  private sentimentTrend: SentimentTrendPoint[] = []
  private _translationEnabled = true

  setTranslationEnabled(enabled: boolean): void {
    this._translationEnabled = enabled
  }

  getTranslationEnabled(): boolean {
    return this._translationEnabled
  }

  async connect(): Promise<void> {
    return new Promise((resolve) => {
      setTimeout(() => {
        this.isConnected = true
        this.openHandlers.forEach((handler) => handler())
        resolve()
      }, 500)
    })
  }

  disconnect(): void {
    this.isConnected = false
    this.stopStreaming()
    this.closeHandlers.forEach((handler) => handler())
  }

  /**
   * 开始从后端接收 VCSum 真实字幕流
   * 使用 SSE 连接到 /api/v1/meeting/subtitles/stream
   */
  startStreaming(): void {
    if (!this.isConnected || this.eventSource) return

    this.sentimentTrend = []

    console.log('[RealDataService] 🔗 正在连接后端 SSE 接口...')
    console.log('[RealDataService] 📊 数据来源：VCSum 数据集')

    // 创建 EventSource 连接后端 SSE 接口
    this.eventSource = new EventSource('/api/v1/meeting/subtitles/stream')

    this.eventSource.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        
        if (message.type === 'subtitle') {
          const subtitle: SubtitleEntry = {
            id: message.data.id,
            speaker: message.data.speaker,
            text: message.data.text,
            timestamp: message.data.timestamp,
            language: message.data.language || 'zh-CN',
          }

          if (this._translationEnabled) {
            this.translateText(subtitle.text, subtitle.language, 'en-US')
              .then((translated) => {
                if (translated) {
                  this.messageHandlers.forEach((handler) =>
                    handler({
                      type: 'subtitle_update',
                      data: { id: subtitle.id, translation: translated },
                    })
                  )
                }
              })
          }

          this.messageHandlers.forEach((handler) =>
            handler({
              type: 'subtitle',
              data: subtitle,
            })
          )

          // 生成对应的情感数据
          const sentiment = this.generateSentiment()
          this.messageHandlers.forEach((handler) =>
            handler({
              type: 'sentiment',
              data: sentiment,
            })
          )

          // 日志输出（显示数据来源）
          const textPreview = 
            subtitle.text.length > 50 
              ? subtitle.text.substring(0, 50) + '...' 
              : subtitle.text
          console.log(`[VCSum] ${subtitle.speaker}: ${textPreview}`)
        
        } else if (message.type === 'stream_complete') {
          console.log(`[RealDataService] ✅ 字幕流推送完成，共 ${message.data.totalSentences} 条`)
          this.eventSource?.close()
          this.eventSource = null
        
        } else if (message.type === 'stream_interrupted') {
          console.log('[RealDataService] ⏹️ 字幕流被中断')
        }
      } catch (error) {
        console.error('[RealDataService] 解析消息失败:', error)
      }
    }

    this.eventSource.onerror = (error) => {
      console.error('[RealDataService] SSE 连接错误:', error)
      this.errorHandlers.forEach((handler) => handler(error))
      
      // 如果连接失败，关闭并清理
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        this.eventSource.close()
        this.eventSource = null
      }
    }

    console.log('[RealDataService] ✅ SSE 连接已建立')
  }

  stopStreaming(): void {
    if (this.eventSource) {
      console.log('[RealDataService] ⏹️ 停止字幕流')
      this.eventSource.close()
      this.eventSource = null
    }
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandlers.push(handler)
  }

  onOpen(handler: ConnectionHandler): void {
    this.openHandlers.push(handler)
  }

  onClose(handler: ConnectionHandler): void {
    this.closeHandlers.push(handler)
  }

  onError(handler: (error: unknown) => void): void {
    this.errorHandlers.push(handler)
  }

  /**
   * 调用翻译 API 将字幕文本翻译为目标语言
   * 使用 POST /api/v1/ai/translate 接口
   */
  private async translateText(text: string, sourceLanguage: string = 'zh-CN', targetLanguage: string = 'en-US'): Promise<string | null> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 10000)

    try {
      const response = await fetch('/api/v1/ai/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, sourceLanguage, targetLanguage }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        console.warn(`[RealDataService] 翻译API返回错误: ${response.status}`)
        return null
      }

      const result = await response.json()
      return result.data?.translatedText ?? null
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.warn('[RealDataService] 翻译请求超时')
      } else {
        console.warn('[RealDataService] 翻译请求失败:', error)
      }
      return null
    }
  }

  /**
   * 基于字幕内容生成情感分析数据
   * 简化版实现，实际应由后端 M4 模块提供
   */
  private generateSentiment(): SentimentData {
    const now = new Date()
    const timeStr = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`

    // 模拟情感波动（实际应调用后端 API）
    const overall = 0.5 + Math.random() * 0.3
    const positive = 0.4 + Math.random() * 0.3
    const negative = 0.15 + Math.random() * 0.2
    const neutral = 0.25 + Math.random() * 0.2
    const engagement = 0.65 + Math.random() * 0.25

    this.sentimentTrend.push({
      time: timeStr,
      value: overall,
    })

    if (this.sentimentTrend.length > 20) {
      this.sentimentTrend = this.sentimentTrend.slice(-20)
    }

    return {
      overall,
      positive,
      negative,
      neutral,
      engagement,
      trend: [...this.sentimentTrend],
    }
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

export const realDataService = new RealDataService()
