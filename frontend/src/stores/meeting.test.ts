import { beforeEach, describe, expect, test, vi } from 'vitest'

const mockHandlers = vi.hoisted(() => ({
  onMessage: undefined as ((data: unknown) => void) | undefined,
  onClose: undefined as (() => void) | undefined,
  onError: undefined as ((error: unknown) => void) | undefined,
}))

const meetingApiMock = vi.hoisted(() => ({
  connect: vi.fn<() => Promise<void>>(),
  disconnect: vi.fn<() => void>(),
  start: vi.fn<(request: unknown) => void>(),
  end: vi.fn<() => void>(),
  onMessage: vi.fn<(handler: (data: unknown) => void) => void>(),
  onClose: vi.fn<(handler: () => void) => void>(),
  onError: vi.fn<(handler: (error: unknown) => void) => void>(),
  isConnected: vi.fn<() => boolean>(),
}))

vi.mock('../services/api', () => ({
  api: {
    meeting: meetingApiMock,
  },
}))

async function loadStore() {
  vi.resetModules()
  const module = await import('./meeting')
  return module.useMeetingStore()
}

function resetApiMocks() {
  mockHandlers.onMessage = undefined
  mockHandlers.onClose = undefined
  mockHandlers.onError = undefined

  meetingApiMock.connect.mockReset()
  meetingApiMock.disconnect.mockReset()
  meetingApiMock.start.mockReset()
  meetingApiMock.end.mockReset()
  meetingApiMock.onMessage.mockReset()
  meetingApiMock.onClose.mockReset()
  meetingApiMock.onError.mockReset()
  meetingApiMock.isConnected.mockReset()

  meetingApiMock.connect.mockResolvedValue(undefined)
  meetingApiMock.disconnect.mockImplementation(() => {
    mockHandlers.onMessage = undefined
    mockHandlers.onClose = undefined
    mockHandlers.onError = undefined
  })
  meetingApiMock.onMessage.mockImplementation((handler) => {
    mockHandlers.onMessage = handler
  })
  meetingApiMock.onClose.mockImplementation((handler) => {
    mockHandlers.onClose = handler
  })
  meetingApiMock.onError.mockImplementation((handler) => {
    mockHandlers.onError = handler
  })
  meetingApiMock.isConnected.mockReturnValue(true)
}

beforeEach(() => {
  resetApiMocks()
})

describe('useMeetingStore websocket lifecycle', () => {
  test('keeps runtime surface visible when the socket closes before a final report', async () => {
    const store = await loadStore()

    await store.startMeeting()
    mockHandlers.onClose?.()

    expect(store.showRuntimeSurface.value).toBe(true)
    expect(store.isRunning.value).toBe(false)
    expect(store.liveError.value).toBe('网关连接已断开，请重新开始会议。')
  })

  test('clears the runtime surface after the final report and ignores the expected close', async () => {
    const store = await loadStore()

    await store.startMeeting()
    mockHandlers.onMessage?.({
      type: 'meeting_end_report',
      data: {
        summary: { summary: '会议已完成。', structured: {} },
        actions: { parsed_actions: [] },
        sentiment: null,
      },
    })
    mockHandlers.onClose?.()

    expect(store.summaryStatus.value).toBe('ready')
    expect(store.showRuntimeSurface.value).toBe(false)
    expect(store.liveError.value).toBeNull()
  })

  test('disconnects before each new start so websocket handlers cannot accumulate', async () => {
    const store = await loadStore()

    await store.startMeeting()
    await store.startMeeting()

    expect(meetingApiMock.disconnect).toHaveBeenCalledTimes(2)
    expect(meetingApiMock.connect).toHaveBeenCalledTimes(2)
    expect(meetingApiMock.start).toHaveBeenCalledTimes(2)
  })

  test('uses the wildcard audio glob by default when the directory fields are hidden', async () => {
    const store = await loadStore()

    await store.startMeeting()

    expect(meetingApiMock.start).toHaveBeenCalledWith(
      expect.objectContaining({
        globPattern: '*',
      }),
    )
  })
})
