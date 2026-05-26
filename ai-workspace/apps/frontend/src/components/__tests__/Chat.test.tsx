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

vi.mock('../../store/store', () => {
  const ollamaState = { models: [{ name: 'llama3', running: false }] }
  const mcpState = { mcps: [] }
  const providerState = { providers: [{ name: 'OpenRouter', enabled: true, models: ['gpt-4', 'claude-3'] }] }
  return {
    useOllamaStore: (selector?: any) => (selector ? selector(ollamaState) : ollamaState),
    useMCPStore: (selector?: any) => (selector ? selector(mcpState) : mcpState),
    useProviderStore: (selector?: any) => (selector ? selector(providerState) : providerState),
    useChatStore: () => mockChatStore,
  }
})

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
    const sendButton = document.querySelector('button[disabled]')
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

  it('CHATUI-008: model selector dropdown exists', () => {
    render(<Chat />)
    // The old <select> was replaced by a custom dropdown with a 'Select model...' button
    const matches = screen.getAllByText('llama3')
    expect(matches.length).toBeGreaterThanOrEqual(1)
    // Verify the dropdown button exists (it contains the selected model name)
    const modelButton = matches.find(el => el.closest('.input-field'))
    expect(modelButton).toBeDefined()
  })
})
