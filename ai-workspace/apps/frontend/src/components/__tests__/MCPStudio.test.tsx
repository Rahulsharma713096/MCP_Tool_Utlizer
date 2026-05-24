import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import MCPStudio from '../../pages/MCPStudio'

vi.mock('../../store/store', () => ({
  useMCPStore: () => ({
    mcps: [
      { name: 'Filesystem', enabled: true, type: 'filesystem', status: 'healthy' },
      { name: 'Browser', enabled: false, type: 'browser', status: 'disabled' },
    ],
  }),
  useOllamaStore: () => ({ models: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
}))

describe('MCPStudio', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('MCPUI-001: renders MCP studio', () => {
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
})
