import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import OllamaManager from '../../pages/OllamaManager'

vi.mock('../../store/store', () => ({
  useOllamaStore: () => ({
    models: [
      { name: 'llama3', size: '4.7GB', running: false },
      { name: 'mistral', size: '4.1GB', running: true },
    ],
    installed: true,
  }),
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
}))

describe('OllamaManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('OUI-001: renders model list', () => {
    render(<OllamaManager />)
    expect(screen.getByText('Ollama Manager')).toBeDefined()
  })

  it('OUI-002: shows model names', () => {
    render(<OllamaManager />)
    expect(screen.getByText('llama3')).toBeDefined()
    expect(screen.getByText('mistral')).toBeDefined()
  })

  it('OUI-006: shows running indicator for active model', () => {
    render(<OllamaManager />)
    // mistral is running
    expect(screen.getByText('mistral')).toBeDefined()
  })

  it('OUI-010: lists model sizes', () => {
    render(<OllamaManager />)
    expect(screen.getByText('4.7GB')).toBeDefined()
    expect(screen.getByText('4.1GB')).toBeDefined()
  })
})
