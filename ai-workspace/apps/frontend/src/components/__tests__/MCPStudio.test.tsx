import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import MCPStudio from '../../pages/MCPStudio'

const mockMcps: any[] = [
  { id: 1, name: 'Filesystem', enabled: true, type: 'filesystem', status: 'healthy', transport: 'stdio' },
  { id: 2, name: 'Browser', enabled: false, type: 'browser', status: 'disabled', transport: 'http', endpoint: 'http://localhost:3001' },
]

const mockMCPStore = {
  mcps: mockMcps,
  addMcp: vi.fn(),
  removeMcp: vi.fn(),
  toggleMcp: vi.fn(),
}

vi.mock('../../store/store', () => ({
  useMCPStore: () => mockMCPStore,
  useOllamaStore: () => ({ models: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
  getStatusDot: (status: string) => status === 'active' ? 'bg-emerald-500' : 'bg-gray-500',
  getStatusColor: (status: string) => 'text-gray-400 bg-gray-500/10',
  formatBytes: (b: number) => `${b} B`,
  formatTimestamp: () => '12:00:00',
}))

describe('MCPStudio', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockMCPStore.mcps = [...mockMcps]
  })

  it('MCPUI-001: renders MCP studio title', () => {
    render(<MCPStudio />)
    expect(screen.getByText('MCP Studio')).toBeDefined()
  })

  it('MCPUI-001: shows MCP names', () => {
    render(<MCPStudio />)
    expect(screen.getByText('Filesystem')).toBeDefined()
    expect(screen.getByText('Browser')).toBeDefined()
  })

  it('MCPUI-007: disabled MCP is rendered', () => {
    render(<MCPStudio />)
    expect(screen.getByText('Browser')).toBeDefined()
  })

  it('MCPUI-006: shows MCP types', () => {
    render(<MCPStudio />)
    expect(screen.getByText('filesystem')).toBeDefined()
  })

  it('MCPUI-008: shows add MCP button', () => {
    render(<MCPStudio />)
    expect(screen.getByText('Add MCP')).toBeDefined()
  })
})
