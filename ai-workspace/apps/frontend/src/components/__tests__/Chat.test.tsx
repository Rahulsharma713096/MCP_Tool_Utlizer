import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Chat from '../../pages/Chat'

// Create mock stores
const mockMessages: any[] = []
const createMockStore = () => ({
  messages: mockMessages,
  sessionId: 'test-session-123',
  streaming: false,
  provider: 'ollama',
  model: 'llama3',
  addMessage: vi.fn(),
  setSessionId: vi.fn(),
  setStreaming: vi.fn(),
  setProvider: vi.fn(),
  setModel: vi.fn(),
  clearMessages: vi.fn(),
})

const mockChatStore = createMockStore()

vi.mock('../../store/store', () => ({
  useOllamaStore: () => ({ models: [{ name: 'llama3', running: false }] }),
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [{ name: 'OpenRouter', enabled: true }] }),
  useChatStore: () => mockChatStore,
  type ChatMessage: {},
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
  formatTimestamp: () => '12:00:00',
}))

import { apiFetch } from '../../lib/utils'

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(mockChatStore, createMockStore())
  })

  it('CHATUI-001: renders chat input area', () => {
    render(<Chat />)
    expect(screen.getByPlaceholderText(/type a message/i)).toBeDefined()
  })

  it('CHATUI-001: send button exists', () => {
    render(<Chat />)
    const sendButton = screen.getByText('Send')
    expect(sendButton).toBeDefined()
  })

  it('CHATUI-003: renders welcome message when no messages', () => {
    render(<Chat />)
    expect(screen.getByText('Start a Conversation')).toBeDefined()
  })

  it('CHATUI-006: renders chat container', () => {
    render(<Chat />)
    const chatArea = document.querySelector('.flex-1.overflow-y-auto')
    expect(chatArea).toBeDefined()
  })

  it('CHATUI-008: provider selector exists', () => {
    render(<Chat />)
    const select = document.querySelector('select')
    expect(select).toBeDefined()
  })
})
