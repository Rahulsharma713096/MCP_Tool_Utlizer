import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Plus, Trash2, TestTube, Globe, Power, Send, MessageSquare, X, RefreshCw, Search, CheckCircle2, AlertTriangle, Loader2, ChevronDown } from 'lucide-react'
import { toast } from 'sonner'
import { cn, apiFetch } from '@/lib/utils'
import { useProviderStore, type Provider } from '@/store/store'

const PROVIDER_PRESETS: Record<string, { base_url: string; models: string[] }> = {
  OpenRouter: { base_url: 'https://openrouter.ai/api/v1', models: [] },
  OpenAI: { base_url: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
  Gemini: { base_url: 'https://generativelanguage.googleapis.com', models: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'] },
  Anthropic: { base_url: 'https://api.anthropic.com', models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'] },
  Claude: { base_url: 'https://api.anthropic.com', models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022'] },
  'Z.ai': { base_url: 'https://api.z.ai/v1', models: ['z-ai-llama-3.1-8b'] },
}

export default function Providers() {
  const { providers, addProvider, updateProvider, removeProvider } = useProviderStore()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newProvider, setNewProvider] = useState({ name: '', base_url: '', api_key: '' })

  // Provider form state
  const [fetchedModels, setFetchedModels] = useState<string[]>([])
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [modelSearch, setModelSearch] = useState('')
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [customModel, setCustomModel] = useState('')
  const [fetchingModels, setFetchingModels] = useState(false)
  const [modelSource, setModelSource] = useState('')
  const [customProviderName, setCustomProviderName] = useState('')

  // Testing state
  const [testingProvider, setTestingProvider] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ provider: string; status: string; latency_ms?: number } | null>(null)

  // Test chat state
  const [testChatProvider, setTestChatProvider] = useState<string | null>(null)
  const [testInput, setTestInput] = useState('')
  const [testResponse, setTestResponse] = useState('')
  const [testLoading, setTestLoading] = useState(false)

  const modelDropdownRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Load provider config from backend on mount
  useEffect(() => {
    async function loadProviderConfig() {
      try {
        const data = await apiFetch<{ providers: Provider[] }>('/providers/config')
        if (data.providers && data.providers.length > 0) {
          data.providers.forEach((p) => addProvider({
            name: p.name,
            enabled: false,
            base_url: p.base_url,
            models: p.models || [],
            status: 'inactive',
          }))
        }
      } catch {
        // Fallback defaults
        Object.entries(PROVIDER_PRESETS).forEach(([name, preset]) => {
          addProvider({
            name,
            enabled: false,
            base_url: preset.base_url,
            models: preset.models,
            status: 'inactive',
          })
        })
      }
    }
    loadProviderConfig()
  }, [])

  // Close model dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setShowModelDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Auto-fill base URL when selecting a preset
  useEffect(() => {
    const name = newProvider.name === '__custom__' ? customProviderName.trim() : newProvider.name
    if (name && PROVIDER_PRESETS[name]) {
      setNewProvider((prev) => ({ ...prev, base_url: PROVIDER_PRESETS[name].base_url }))
    }
  }, [newProvider.name, customProviderName])

  // Filter models by search
  const filteredModels = useMemo(() => {
    if (!modelSearch.trim()) return fetchedModels
    const q = modelSearch.toLowerCase()
    return fetchedModels.filter((m) => m.toLowerCase().includes(q))
  }, [fetchedModels, modelSearch])

  const handleFetchModels = useCallback(async () => {
    const providerName = newProvider.name === '__custom__' ? customProviderName.trim() : newProvider.name
    if (!providerName || !newProvider.base_url) {
      toast.error('Enter provider name and base URL first')
      return
    }
    setFetchingModels(true)
    setModelSource('')
    try {
      const data = await apiFetch<{ models: string[]; source: string; count?: number; message?: string }>(
        '/providers/fetch-models',
        {
          method: 'POST',
          body: JSON.stringify({ name: providerName, base_url: newProvider.base_url, api_key: newProvider.api_key || undefined }),
        }
      )
      setFetchedModels(data.models || [])
      setModelSource(data.source || 'unknown')
      if (data.count) {
        toast.success(`Fetched ${data.count} models from ${providerName}`)
      } else if (data.message) {
        toast.info(data.message)
      }
      setSelectedModels(data.models || [])
    } catch (err: any) {
      toast.error(`Failed to fetch models: ${err.message}`)
      const preset = PROVIDER_PRESETS[providerName]
      if (preset?.models) {
        setFetchedModels(preset.models)
        setSelectedModels(preset.models)
        setModelSource('suggestions')
        toast.info(`Using suggested models for ${providerName}`)
      }
    } finally {
      setFetchingModels(false)
    }
  }, [newProvider.name, customProviderName, newProvider.base_url, newProvider.api_key])

  const handleAddCustomModel = () => {
    if (!customModel.trim()) return
    const model = customModel.trim()
    if (!fetchedModels.includes(model)) {
      setFetchedModels((prev) => [...prev, model])
    }
    if (!selectedModels.includes(model)) {
      setSelectedModels((prev) => [...prev, model])
    }
    setCustomModel('')
    toast.success(`Added model: ${model}`)
  }

  const handleAdd = async () => {
    const providerName = newProvider.name === '__custom__' ? customProviderName.trim() : newProvider.name
    if (!providerName || !newProvider.base_url) {
      toast.error('Name and Base URL are required')
      return
    }
    try {
      const result = await apiFetch<{ status: string }>('/providers', {
        method: 'POST',
        body: JSON.stringify({
          name: providerName,
          base_url: newProvider.base_url,
          api_key: newProvider.api_key || undefined,
        }),
      })
      addProvider({
        name: providerName,
        enabled: true,
        base_url: newProvider.base_url,
        models: selectedModels.length > 0 ? selectedModels : (PROVIDER_PRESETS[providerName]?.models || []),
        status: 'active',
      })
      setNewProvider({ name: '', base_url: '', api_key: '' })
      setCustomProviderName('')
      setSelectedModels([])
      setFetchedModels([])
      setModelSearch('')
      setShowAddForm(false)
      toast.success(`${result.status === 'updated' ? 'Updated' : 'Added'} provider: ${providerName}`)
    } catch (err: any) {
      toast.error(`Failed to add provider: ${err.message}`)
    }
  }

  const testConnection = async (provider: Provider) => {
    setTestingProvider(provider.name)
    setTestResult(null)
    try {
      const result = await apiFetch<{ status: string; latency_ms?: number; message?: string }>('/providers/test', {
        method: 'POST',
        body: JSON.stringify({ name: provider.name, base_url: provider.base_url, api_key: '' }),
      })
      setTestResult({ provider: provider.name, status: result.status, latency_ms: result.latency_ms })
      if (result.status === 'healthy') {
        toast.success(`${provider.name} connected${result.latency_ms ? ` (${result.latency_ms}ms)` : ''}`)
      } else {
        toast.error(`${provider.name}: ${result.status}${result.message ? ` -- ${result.message}` : ''}`)
      }
    } catch (err: any) {
      setTestResult({ provider: provider.name, status: 'error' })
      toast.error(`${provider.name} test failed: ${err.message}`)
    } finally {
      setTestingProvider(null)
    }
  }

  const toggleProvider = async (provider: Provider) => {
    const newEnabled = !provider.enabled
    try {
      if (newEnabled) {
        await apiFetch('/providers', {
          method: 'POST',
          body: JSON.stringify({ name: provider.name, base_url: provider.base_url }),
        })
      }
      updateProvider(provider.name, { enabled: newEnabled, status: newEnabled ? 'active' : 'inactive' })
      toast.success(`${newEnabled ? 'Enabled' : 'Disabled'} ${provider.name}`)
    } catch (err: any) {
      toast.error(`Failed to toggle ${provider.name}: ${err.message}`)
    }
  }

  const handleTestChat = async (providerName: string) => {
    if (!testInput.trim()) return
    setTestLoading(true)
    setTestResponse('')
    try {
      const provider = providers.find((p) => p.name === providerName)
      if (!provider) {
        setTestResponse('Error: Provider not found')
        setTestLoading(false)
        return
      }
      const result = await apiFetch<{ success: boolean; response: string }>('/providers/test-chat', {
        method: 'POST',
        body: JSON.stringify({
          name: providerName,
          base_url: provider.base_url,
          selected_model: provider.models?.[0] || undefined,
        }),
      })
      setTestResponse(result.response || 'No response')
    } catch (err: any) {
      setTestResponse(`Error: ${err.message}`)
    } finally {
      setTestLoading(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Provider Manager</h1>
          <p className="page-description">Configure online AI providers with dynamic model loading</p>
        </div>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add Provider
        </button>
      </div>

      {/* Add Provider Form */}
      {showAddForm && (
        <div className="glass-panel p-4 animate-slide-up">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Configure New Provider</h3>

          {/* Provider Name (preset selector) */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Provider</label>
              <select
                value={newProvider.name}
                onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                className="input-field"
              >
                <option value="">Select provider...</option>
                {Object.keys(PROVIDER_PRESETS).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
                <option value="__custom__">Custom Provider</option>
              </select>
              {newProvider.name === '__custom__' && (
                <input
                  value={customProviderName}
                  onChange={(e) => setCustomProviderName(e.target.value)}
                  placeholder="Enter custom provider name"
                  className="input-field mt-2"
                  autoFocus
                />
              )}
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Base URL</label>
              <input
                value={newProvider.base_url}
                onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })}
                placeholder="https://api.example.com/v1"
                className="input-field"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">API Key</label>
              <input
                type="password"
                value={newProvider.api_key}
                onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })}
                placeholder="sk-..."
                className="input-field"
              />
            </div>
          </div>

          {/* Model Selection */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <label className="text-xs text-gray-500">Models</label>
              <button
                onClick={handleFetchModels}
                disabled={fetchingModels || (!newProvider.name && !customProviderName.trim())}
                className="text-xs px-2 py-1 rounded bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                {fetchingModels ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                {fetchingModels ? 'Fetching...' : 'Fetch Models'}
              </button>
              {modelSource && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">
                  source: {modelSource}
                </span>
              )}
            </div>

            {/* Model Search + Manual Input */}
            {fetchedModels.length > 0 && (
              <div className="relative mb-2" ref={modelDropdownRef}>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="w-3 h-3 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input
                      ref={searchInputRef}
                      value={modelSearch}
                      onChange={(e) => { setModelSearch(e.target.value); setShowModelDropdown(true) }}
                      onFocus={() => setShowModelDropdown(true)}
                      placeholder={`Search ${fetchedModels.length} models...`}
                      className="input-field pl-8 text-xs"
                    />
                  </div>
                  <div className="flex gap-1">
                    <input
                      value={customModel}
                      onChange={(e) => setCustomModel(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddCustomModel() } }}
                      placeholder="Add custom model"
                      className="input-field text-xs w-48"
                    />
                    <button onClick={handleAddCustomModel} className="btn-secondary text-xs px-2">Add</button>
                  </div>
                </div>

                {/* Model dropdown */}
                {showModelDropdown && filteredModels.length > 0 && (
                  <div className="absolute top-full mt-1 w-full bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto">
                    <div className="p-2 border-b border-gray-800 flex items-center justify-between">
                      <button
                        onClick={() => { setSelectedModels(filteredModels); setShowModelDropdown(false) }}
                        className="text-[10px] text-cyan-400 hover:text-cyan-300"
                      >
                        Select all ({filteredModels.length})
                      </button>
                      <button
                        onClick={() => { setSelectedModels([]); setShowModelDropdown(false) }}
                        className="text-[10px] text-gray-500 hover:text-gray-400"
                      >
                        Clear
                      </button>
                    </div>
                    {filteredModels.map((model) => {
                      const isSelected = selectedModels.includes(model)
                      return (
                        <button
                          key={model}
                          onClick={() => {
                            setSelectedModels((prev) =>
                              isSelected ? prev.filter((m) => m !== model) : [...prev, model]
                            )
                          }}
                          className={cn(
                            'w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors',
                            isSelected ? 'bg-cyan-500/10 text-cyan-300' : 'text-gray-300 hover:bg-gray-800'
                          )}
                        >
                          <div className={cn(
                            'w-3.5 h-3.5 rounded border flex items-center justify-center shrink-0',
                            isSelected ? 'bg-cyan-500 border-cyan-500' : 'border-gray-600'
                          )}>
                            {isSelected && <CheckCircle2 className="w-3 h-3 text-white" />}
                          </div>
                          <span className="truncate">{model}</span>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Selected models chips */}
            {selectedModels.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {selectedModels.map((m) => (
                  <span key={m} className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    {m}
                    <button onClick={() => setSelectedModels((prev) => prev.filter((x) => x !== m))} className="hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {fetchedModels.length === 0 && !fetchingModels && (
              <p className="text-xs text-gray-600 mt-1">Click "Fetch Models" to load available models from the provider API</p>
            )}
          </div>

          <div className="flex gap-2">
            <button onClick={handleAdd} className="btn-primary">Save Provider</button>
            <button onClick={() => { setShowAddForm(false); setFetchedModels([]); setSelectedModels([]) }} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* Provider Cards */}
      <div className="grid gap-4">
        {providers.map((provider) => (
          <div key={provider.name} className="glass-card flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', provider.enabled ? 'bg-emerald-500/10' : 'bg-gray-800')}>
                <Globe className={cn('w-5 h-5', provider.enabled ? 'text-emerald-400' : 'text-gray-600')} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-200">{provider.name}</span>
                  <span className={cn('badge', provider.enabled ? 'badge-active' : 'badge-inactive')}>
                    {provider.enabled ? 'Active' : 'Inactive'}
                  </span>
                  {testResult?.provider === provider.name && (
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded-full',
                      testResult.status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                    )}>
                      {testResult.status} {testResult.latency_ms ? `(${testResult.latency_ms}ms)` : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-gray-500 truncate max-w-[200px]">{provider.base_url}</span>
                  {provider.models && provider.models.length > 0 && (
                    <span className="text-[10px] text-gray-600 border border-gray-700 rounded px-1.5 py-0.5">
                      {provider.models.length} model{provider.models.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => testConnection(provider)}
                disabled={testingProvider === provider.name}
                className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-cyan-400 transition-all disabled:opacity-50"
                title="Test Connection"
              >
                {testingProvider === provider.name ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <TestTube className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={() => { setTestChatProvider(provider.name); setTestInput(''); setTestResponse('') }}
                className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-purple-400 transition-all"
                title="Test Chat"
              >
                <MessageSquare className="w-4 h-4" />
              </button>
              <button
                onClick={() => toggleProvider(provider)}
                className={cn('p-2 rounded-lg transition-all',
                  provider.enabled ? 'text-emerald-400 hover:bg-emerald-500/10' : 'text-gray-500 hover:bg-gray-800'
                )}
                title={provider.enabled ? 'Disable' : 'Enable'}
              >
                <Power className="w-4 h-4" />
              </button>
              <button
                onClick={() => { removeProvider(provider.name); toast.success(`Removed ${provider.name}`) }}
                className="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all"
                title="Remove"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Test Chat Dialog */}
      {testChatProvider && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setTestChatProvider(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-lg w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">Test Chat — {testChatProvider}</h3>
              <button onClick={() => setTestChatProvider(null)} className="p-1 hover:bg-gray-800 rounded-lg">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            <div className="mb-3">
              <input
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTestChat(testChatProvider) } }}
                placeholder="Type a test message..."
                className="input-field"
              />
            </div>
            <button
              onClick={() => handleTestChat(testChatProvider)}
              disabled={testLoading || !testInput.trim()}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Send className="w-3.5 h-3.5" />
              {testLoading ? 'Sending...' : 'Send'}
            </button>
            {testResponse && (
              <div className="mt-4 p-3 rounded-lg bg-gray-800/50 border border-gray-700/30">
                <p className="text-xs text-gray-500 mb-1">Response:</p>
                <p className="text-sm text-gray-200 whitespace-pre-wrap">{testResponse}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Security Notice */}
      <div className="glass-panel p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">Security Notice</h3>
        <p className="text-xs text-gray-500">
          API keys are stored in-memory only on the server and are never persisted to disk or the browser.
          All provider communication occurs over HTTPS.
        </p>
      </div>
    </div>
  )
}
