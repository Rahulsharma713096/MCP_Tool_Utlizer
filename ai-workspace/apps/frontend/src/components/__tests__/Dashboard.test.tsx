import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '../../pages/Dashboard'

// Mock the stores - vi.mock is hoisted, use vi.hoisted for variables
vi.mock('../../store/store', () => ({
  useOllamaStore: () => ({ models: [] }),
  useMCPStore: () => ({ mcps: [] }),
  useProviderStore: () => ({ providers: [] }),
}))

const mockSystemInfo = {
  cpus: 8,
  total_ram_gb: 32,
  available_ram_gb: 16,
  total_disk_gb: 500,
  free_disk_gb: 200,
  gpu_available: false,
  gpu_name: null,
}

const mockHealthData = {
  status: 'healthy',
  ollama: true,
  active_mcps: 3,
  active_providers: 2,
}

const mockMetricsData = {
  cpu_percent: 45.5,
  ram_percent: 62.3,
  ram_used_gb: 8.2,
  ram_total_gb: 32,
}

// Use vi.hoisted to create mock functions that work with vi.mock hoisting
const { getMockApi } = vi.hoisted(() => {
  const mockApi = vi.fn()
  return { getMockApi: () => mockApi }
})

vi.mock('../../lib/utils', () => ({
  apiFetch: getMockApi(),
  cn: (...inputs: any[]) => inputs.filter(Boolean).join(' '),
}))

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const api = getMockApi()
    // Setup sequential mock returns: /system/info, /health, /system/metrics
    api
      .mockResolvedValueOnce(mockSystemInfo)
      .mockResolvedValueOnce(mockHealthData)
      .mockResolvedValueOnce(mockMetricsData)
      // Subsequent calls from the interval
      .mockResolvedValue(mockSystemInfo)
  })

  it('UI-001: renders dashboard with title', async () => {
    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })

  it('UI-001: shows stat cards', async () => {
    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('CPU Cores')).toBeDefined()
      expect(screen.getByText('RAM')).toBeDefined()
      expect(screen.getByText('Disk')).toBeDefined()
    })
  })

  it('UI-003: renders module cards', async () => {
    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('Ollama Models')).toBeDefined()
      expect(screen.getByText('MCP Servers')).toBeDefined()
      expect(screen.getByText('Providers')).toBeDefined()
      expect(screen.getByText('GPU')).toBeDefined()
    })
  })

  it('UI-001: shows quick actions', async () => {
    render(<Dashboard />)

    await waitFor(() => {
      expect(screen.getByText('Start Chat')).toBeDefined()
      expect(screen.getByText('Manage Models')).toBeDefined()
      expect(screen.getByText('Configure MCP')).toBeDefined()
      expect(screen.getByText('View Metrics')).toBeDefined()
    })
  })

  it('UI-007: handles backend disconnected state', async () => {
    getMockApi().mockReset()
    getMockApi().mockRejectedValue(new Error('Failed to fetch'))

    render(<Dashboard />)

    // Should render without crashing
    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })

  it('UI-005: handles missing data gracefully', async () => {
    getMockApi().mockReset()
    getMockApi().mockResolvedValue(null)

    render(<Dashboard />)

    // Should not crash with null data
    await waitFor(() => {
      expect(screen.getByText('AI Workspace Platform')).toBeDefined()
    })
  })
})
