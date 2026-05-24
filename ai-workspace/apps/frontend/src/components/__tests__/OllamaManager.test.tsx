import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import OllamaManager from '../../pages/OllamaManager'

const mockOllamaStore = {
  installed: true,
  version: '0.3.0',
  models: [
    { name: 'llama3', running: false },
    { name: 'mistral', running: true },
  ],
  loading: false,
  setInstalled: vi.fn(),
  setVersion: vi.fn(),
  setModels: vi.fn(),
  setLoading: vi.fn(),
}

vi.mock('../../store/store', () => ({
  useOllamaStore: () => mockOllamaStore,
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
  getStatusDot: () => 'bg-emerald-500',
  getStatusColor: () => 'text-gray-400 bg-gray-500/10',
  formatBytes: (b: number) => `${b} B`,
  formatTimestamp: () => '12:00:00',
}))

describe('OllamaManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockOllamaStore.installed = true
    mockOllamaStore.version = '0.3.0'
    mockOllamaStore.models = [
      { name: 'llama3', running: false },
      { name: 'mistral', running: true },
    ]
  })

  it('OUI-001: renders model manager title', () => {
    render(<OllamaManager />)
    expect(screen.getByText('Ollama Runtime Manager')).toBeDefined()
  })

  it('OUI-002: shows stats cards', () => {
    render(<OllamaManager />)
    expect(screen.getByText('Models')).toBeDefined()
    expect(screen.getByText('Running')).toBeDefined()
    expect(screen.getByText('Total Size')).toBeDefined()
  })

  it('OUI-003: shows version badge', () => {
    render(<OllamaManager />)
    expect(screen.getByText('0.3.0')).toBeDefined()
  })

  it('OUI-010: shows refresh button', () => {
    render(<OllamaManager />)
    expect(screen.getByText('Refresh')).toBeDefined()
  })
})
