type MessageHandler = (data: unknown) => void;
type ConnectionHandler = () => void;

import type { PipelineStartRequest } from "../types";

class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private openHandlers: ConnectionHandler[] = [];
  private closeHandlers: ConnectionHandler[] = [];
  private errorHandlers: ((error: unknown) => void)[] = [];
  private isConnected = false;

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const wsUrl = `${protocol}://${window.location.hostname}:8000/ws/pipeline/dir`;
      console.log(`[WebSocket] Connecting to ${wsUrl}`);

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[WebSocket] Connected");
        this.isConnected = true;
        this.openHandlers.forEach((h) => h());
        resolve();
      };

      this.ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        this.isConnected = false;
        this.closeHandlers.forEach((h) => h());
      };

      this.ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
        this.errorHandlers.forEach((h) => h(error));
        if (!this.isConnected) {
          reject(error);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.messageHandlers.forEach((h) => h(message));
        } catch (e) {
          console.error("[WebSocket] Parse error:", e);
        }
      };
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
    this.messageHandlers = [];
    this.openHandlers = [];
    this.closeHandlers = [];
    this.errorHandlers = [];
  }

  send(message: Record<string, unknown>): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message));
    }
  }

  startMeeting(request: PipelineStartRequest): void {
    this.send({
      session_id: request.sessionId,
      input_dir: request.inputDir,
      glob_pattern: request.globPattern,
      target_lang: request.targetLang,
      enable_translation: request.enableTranslation,
      enable_actions: request.enableActions,
      enable_sentiment: request.enableSentiment,
    });
  }

  endMeeting(): void {
    this.send({ type: "end_meeting" });
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandlers.push(handler);
  }

  onOpen(handler: ConnectionHandler): void {
    this.openHandlers.push(handler);
  }

  onClose(handler: ConnectionHandler): void {
    this.closeHandlers.push(handler);
  }

  onError(handler: (error: unknown) => void): void {
    this.errorHandlers.push(handler);
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

export const wsService = new WebSocketService();

export const api = {
  meeting: {
    connect: () => wsService.connect(),
    disconnect: () => wsService.disconnect(),
    start: (request: PipelineStartRequest) => wsService.startMeeting(request),
    end: () => wsService.endMeeting(),
    onMessage: (handler: MessageHandler) => wsService.onMessage(handler),
    onOpen: (handler: ConnectionHandler) => wsService.onOpen(handler),
    onClose: (handler: ConnectionHandler) => wsService.onClose(handler),
    onError: (handler: (error: unknown) => void) => wsService.onError(handler),
    isConnected: () => wsService.getConnectionStatus(),
  },
};
