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
  directory?: string
  github_repo?: string
  github_ref?: string
  root?: string
  exclude?: string[]
  command?: string
  args?: string[]
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
  // Note: api_key is NOT persisted to localStorage for security
  // It's kept in-memory only on the frontend side
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
        set((state) => {
          const target = state.models.find((m) => m.name === modelName)
          if (!target) return state
          // If turning ON: stop all others (single model constraint)
          // If turning OFF: just stop this one
          const newRunning = !target.running
          return {
            models: state.models.map((m) => ({
              ...m,
              running: m.name === modelName ? newRunning : (newRunning ? false : m.running),
            })),
          }
        }),
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
      addMcp: (mcp) => set((state) => {
        // Dedup: don't add if same name+type already exists
        const exists = state.mcps.some((m) => m.name === mcp.name && m.type === mcp.type)
        if (exists) return state
        return { mcps: [...state.mcps, mcp] }
      }),
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
// NOTE: api_key is NOT stored here for security.
// Provider registration happens server-side via POST /providers.
// The store only holds display-safe data (name, models, status).

interface ProviderState {
  providers: Provider[]
  loading: boolean
  setProviders: (providers: Provider[]) => void
  addProvider: (provider: Provider) => void
  updateProvider: (name: string, updates: Partial<Provider>) => void
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
        set((state) => {
          // Dedup: if provider with same name exists, update it instead
          const exists = state.providers.findIndex((p) => p.name.toLowerCase() === provider.name.toLowerCase())
          if (exists >= 0) {
            const updated = [...state.providers]
            updated[exists] = { ...updated[exists], ...provider }
            return { providers: updated }
          }
          return { providers: [...state.providers, provider] }
        }),
      updateProvider: (name, updates) =>
        set((state) => ({
          providers: state.providers.map((p) =>
            p.name.toLowerCase() === name.toLowerCase() ? { ...p, ...updates } : p
          ),
        })),
      removeProvider: (name) =>
        set((state) => ({
          providers: state.providers.filter((p) => p.name.toLowerCase() !== name.toLowerCase()),
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
    {
      name: 'chat-store',
      partialize: (state) => {
        // Don't persist streaming state — it's a runtime-only flag
        const { streaming, ...rest } = state
        return rest
      },
    }
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
