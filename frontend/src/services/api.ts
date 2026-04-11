import type { SubtitleEntry, SentimentData, MeetingSummary } from '../types'

type MessageHandler = (data: unknown) => void
type ConnectionHandler = () => void

interface MeetingStartedData {
  meeting_id: string
  mode: string
  start_time: string
}

interface MeetingEndReportData {
  summary: { summary?: string; structured?: Record<string, unknown> }
  actions: { action_items?: Array<{ task: string; assignee?: string; deadline?: string }> }
  full_text: string
}

class WebSocketService {
  private ws: WebSocket | null = null
  private messageHandlers: MessageHandler[] = []
  private openHandlers: ConnectionHandler[] = []
  private closeHandlers: ConnectionHandler[] = []
  private errorHandlers: ((error: unknown) => void)[] = []
  private isConnected = false
  private sessionId: string = `session_${Date.now()}`
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `ws://${window.location.hostname}:8000/ws/meeting/${this.sessionId}`
      console.log(`[WebSocket] Connecting to ${wsUrl}`)

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.openHandlers.forEach((h) => h())
        resolve()
      }

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected')
        this.isConnected = false
        this.closeHandlers.forEach((h) => h())
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        this.errorHandlers.forEach((h) => h(error))
        if (!this.isConnected) {
          reject(error)
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.messageHandlers.forEach((h) => h(message))
        } catch (e) {
          console.error('[WebSocket] Parse error:', e)
        }
      }
    })
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.isConnected = false
    }
    this.messageHandlers = []
    this.openHandlers = []
    this.closeHandlers = []
    this.errorHandlers = []
  }

  send(message: Record<string, unknown>): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message))
    }
  }

  startMeeting(
    mode: 'demo' | 'realtime' = 'demo',
    inputDir?: string,
    targetLang?: 'zh' | 'en' | 'ja',
  ): void {
    this.send({ type: 'start_meeting', mode, input_dir: inputDir, target_lang: targetLang })
  }

  endMeeting(): void {
    this.send({ type: 'end_meeting' })
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

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

export const wsService = new WebSocketService()

export const api = {
  meeting: {
    connect: () => wsService.connect(),
    disconnect: () => wsService.disconnect(),
    start: (
      mode: 'demo' | 'realtime' = 'demo',
      inputDir?: string,
      targetLang?: 'zh' | 'en' | 'ja',
    ) => wsService.startMeeting(mode, inputDir, targetLang),
    end: () => wsService.endMeeting(),
    onMessage: (handler: MessageHandler) => wsService.onMessage(handler),
    onOpen: (handler: ConnectionHandler) => wsService.onOpen(handler),
    onClose: (handler: ConnectionHandler) => wsService.onClose(handler),
    onError: (handler: (error: unknown) => void) => wsService.onError(handler),
    isConnected: () => wsService.getConnectionStatus(),
  },
}
