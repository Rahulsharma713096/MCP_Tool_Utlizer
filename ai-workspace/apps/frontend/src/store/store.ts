import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ============== Types ==============

export interface Model {
  name: string
  size?: string
  quantization?: string
  running: boolean
  cpu_usage: number
  ram_usage: number
  pid?: number
}

export interface MCP {
  id: number
  name: string
  type: string
  enabled: boolean
  status: string
  transport: string
  endpoint?: string
  // Directory for filesystem MCP (allowed directory access)
  directory?: string
  // GitHub repo configuration for npx-based MCPs
  github_repo?: string
  github_ref?: string
  root?: string
  exclude?: string[]
  command?: string
  args?: string[]
  // Environment variables to pass to the MCP server
  env?: Record<string, string>
}

export interface Provider {
  name: string
  enabled: boolean
  base_url: string
  models: string[]
  selected_model?: string
  status: string
  latency_ms?: number
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
}

export interface SystemMetrics {
  cpu_percent: number
  ram_percent: number
  ram_used_gb: number
  gpu_percent?: number
  vram_used_gb?: number
  active_models: number
  active_mcps: number
  timestamp: string
}

export type Theme = 'neon' | 'glass' | 'cyberpunk' | 'minimal' | 'enterprise'

// ============== UI Store ==============

interface UIState {
  sidebarCollapsed: boolean
  theme: Theme
  activePage: string
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setTheme: (theme: Theme) => void
  setActivePage: (page: string) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'neon' as Theme,
      activePage: 'dashboard',
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
      setActivePage: (page) => set({ activePage: page }),
    }),
    { name: 'ui-store' }
  )
)

// ============== Ollama Store ==============

interface OllamaState {
  installed: boolean
  version: string | null
  models: Model[]
  loading: boolean
  error: string | null
  setInstalled: (installed: boolean) => void
  setVersion: (version: string | null) => void
  setModels: (models: Model[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  toggleModel: (modelName: string) => void
  startModelOnly: (modelName: string) => void
  stopAllModels: () => void
}

export const useOllamaStore = create<OllamaState>()(
  persist(
    (set) => ({
      installed: false,
      version: null,
      models: [],
      loading: false,
      error: null,
      setInstalled: (installed) => set({ installed }),
      setVersion: (version) => set({ version }),
      setModels: (models) => set({ models }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      toggleModel: (modelName) =>
        set((state) => ({
          models: state.models.map((m) =>
            m.name === modelName ? { ...m, running: !m.running } : m
          ),
        })),
      startModelOnly: (modelName) =>
        set((state) => ({
          models: state.models.map((m) => ({
            ...m,
            running: m.name === modelName,
          })),
        })),
      stopAllModels: () =>
        set((state) => ({
          models: state.models.map((m) => ({ ...m, running: false })),
        })),
    }),
    { name: 'ollama-store' }
  )
)

// ============== MCP Store ==============

interface MCPState {
  mcps: MCP[]
  loading: boolean
  setMcps: (mcps: MCP[]) => void
  addMcp: (mcp: MCP) => void
  removeMcp: (id: number) => void
  toggleMcp: (id: number) => void
  setLoading: (loading: boolean) => void
}

export const useMCPStore = create<MCPState>()(
  persist(
    (set) => ({
      mcps: [],
      loading: false,
      setMcps: (mcps) => set({ mcps }),
      addMcp: (mcp) => set((state) => ({ mcps: [...state.mcps, mcp] })),
      removeMcp: (id) =>
        set((state) => ({ mcps: state.mcps.filter((m) => m.id !== id) })),
      toggleMcp: (id) =>
        set((state) => ({
          mcps: state.mcps.map((m) =>
            m.id === id ? { ...m, enabled: !m.enabled } : m
          ),
        })),
      setLoading: (loading) => set({ loading }),
    }),
    { name: 'mcp-store' }
  )
)

// ============== Provider Store ==============

interface ProviderState {
  providers: Provider[]
  loading: boolean
  setProviders: (providers: Provider[]) => void
  addProvider: (provider: Provider) => void
  removeProvider: (name: string) => void
  setLoading: (loading: boolean) => void
}

export const useProviderStore = create<ProviderState>()(
  persist(
    (set) => ({
      providers: [],
      loading: false,
      setProviders: (providers) => set({ providers }),
      addProvider: (provider) =>
        set((state) => ({ providers: [...state.providers, provider] })),
      removeProvider: (name) =>
        set((state) => ({
          providers: state.providers.filter((p) => p.name !== name),
        })),
      setLoading: (loading) => set({ loading }),
    }),
    { name: 'provider-store' }
  )
)

// ============== Chat Store ==============

interface ChatState {
  messages: ChatMessage[]
  sessionId: string | null
  streaming: boolean
  provider: string
  model: string
  addMessage: (message: ChatMessage) => void
  setSessionId: (id: string) => void
  setStreaming: (streaming: boolean) => void
  setProvider: (provider: string) => void
  setModel: (model: string) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      sessionId: null,
      streaming: false,
      provider: 'ollama',
      model: 'llama3',
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      setSessionId: (id) => set({ sessionId: id }),
      setStreaming: (streaming) => set({ streaming }),
      setProvider: (provider) => set({ provider }),
      setModel: (model) => set({ model }),
      clearMessages: () => set({ messages: [] }),
    }),
    { name: 'chat-store' }
  )
)

// ============== Metrics Store ==============

interface MetricsState {
  history: SystemMetrics[]
  current: SystemMetrics | null
  addMetric: (metric: SystemMetrics) => void
  setCurrent: (metric: SystemMetrics) => void
}

export const useMetricsStore = create<MetricsState>()((set) => ({
  history: [],
  current: null,
  addMetric: (metric) =>
    set((state) => ({
      history: [...state.history.slice(-100), metric],
    })),
  setCurrent: (metric) => set({ current: metric }),
}))
