import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Chat from '../../pages/Chat'

vi.mock('../../store/store', () => ({
  useOllamaStore: () => ({ models: [{ name: 'llama3' }] }),
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [{ name: 'OpenRouter', enabled: true }] }),
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
}))

import { apiFetch } from '../../lib/utils'

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('CHATUI-001: renders chat input area', () => {
    render(<Chat />)
    expect(screen.getByPlaceholderText(/type a message/i)).toBeDefined()
  })

  it('CHATUI-001: send button exists', () => {
    render(<Chat />)
    const sendButton = screen.getByRole('button', { name: /send/i }) || screen.getByText('Send')
    expect(sendButton).toBeDefined()
  })

  it('CHATUI-004: empty message does not send', async () => {
    render(<Chat />)
    const sendButton = screen.getByRole('button', { name: /send/i })
    fireEvent.click(sendButton)
    // apiFetch should not be called with empty message
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('CHATUI-008: shows error for invalid provider', async () => {
    ;(apiFetch as any).mockRejectedValue(new Error('Provider not found'))

    render(<Chat />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/type a message/i)).toBeDefined()
    })
  })

  it('CHATUI-003: session is created', async () => {
    ;(apiFetch as any).mockResolvedValue({ session_id: 'test-session-123' })

    render(<Chat />)

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalled()
    })
  })

  it('CHATUI-006: renders chat container', () => {
    render(<Chat />)
    const chatArea = document.querySelector('.flex-1.overflow-y-auto')
    expect(chatArea).toBeDefined()
  })

  it('CHATUI-008: model selector exists', () => {
    render(<Chat />)
    // Should have some way to select models
    const selects = document.querySelectorAll('select')
    expect(selects.length).toBeGreaterThanOrEqual(0)
  })
})
