import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '../../pages/Dashboard'

// Mock the stores
vi.mock('../../store/store', () => ({
  useOllamaStore: () => ({ models: [] }),
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

// Mock apiFetch
vi.mock('../../lib/utils', () => ({
  apiFetch: vi.fn(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
}))

import { apiFetch } from '../../lib/utils'

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('UI-001: renders dashboard with title', async () => {
    ;(apiFetch as any).mockResolvedValue({
      cpus: 8,
      total_ram_gb: 32,
      available_ram_gb: 16,
      total_disk_gb: 500,
      free_disk_gb: 200,
      gpu_available: false,
      gpu_name: null,
    })

    ;(apiFetch as any).mockResolvedValueOnce({
      status: 'healthy',
      ollama: true,
      active_mcps: 3,
      active_providers: 2,
    })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })

  it('UI-001: shows stat cards', async () => {
    ;(apiFetch as any).mockResolvedValue({
      cpus: 8,
      total_ram_gb: 32,
      available_ram_gb: 16,
      total_disk_gb: 500,
      free_disk_gb: 200,
    })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('CPU Cores')).toBeDefined()
      expect(screen.getByText('RAM')).toBeDefined()
      expect(screen.getByText('Disk')).toBeDefined()
    })
  })

  it('UI-001: shows health status', async () => {
    const mockHealth = {
      status: 'healthy',
      ollama: true,
      active_mcps: 3,
      active_providers: 2,
    }

    ;(apiFetch as any).mockResolvedValue({
      cpus: 8,
      total_ram_gb: 32,
      available_ram_gb: 16,
      total_disk_gb: 500,
      free_disk_gb: 200,
    })

    ;(apiFetch as any).mockResolvedValueOnce(mockHealth)

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText(/System healthy/)).toBeDefined()
    })
  })

  it('UI-003: renders module cards', async () => {
    ;(apiFetch as any).mockResolvedValue({
      cpus: 8,
      total_ram_gb: 32,
      available_ram_gb: 16,
      total_disk_gb: 500,
      free_disk_gb: 200,
    })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('Ollama Models')).toBeDefined()
      expect(screen.getByText('MCP Servers')).toBeDefined()
      expect(screen.getByText('Providers')).toBeDefined()
      expect(screen.getByText('GPU')).toBeDefined()
    })
  })

  it('UI-001: shows quick actions', async () => {
    ;(apiFetch as any).mockResolvedValue({
      cpus: 8,
      total_ram_gb: 32,
      available_ram_gb: 16,
    })

    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('Start Chat')).toBeDefined()
      expect(screen.getByText('Manage Models')).toBeDefined()
      expect(screen.getByText('Configure MCP')).toBeDefined()
      expect(screen.getByText('View Metrics')).toBeDefined()
    })
  })

  it('UI-007: handles backend disconnected state', async () => {
    ;(apiFetch as any).mockRejectedValue(new Error('Failed to fetch'))

    render(<Dashboard />)

    // Should render without crashing
    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })

  it('UI-005: handles missing data gracefully', async () => {
    ;(apiFetch as any).mockResolvedValue(null)

    render(<Dashboard />)

    // Should not crash with null data
    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })
})
