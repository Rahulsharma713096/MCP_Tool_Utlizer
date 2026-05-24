import '@testing-library/jest-dom'

// Mock scrollIntoView for jsdom environment
Element.prototype.scrollIntoView = vi.fn() as any

// Mock WebSocket for Chat tests
class MockWebSocket {
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: (() => void) | null = null
  readyState: number = WebSocket.OPEN

  constructor(_url: string) {}

  send(_data: string): void {}

  close(): void {
    this.onclose?.()
  }
}

vi.stubGlobal('WebSocket', MockWebSocket)
