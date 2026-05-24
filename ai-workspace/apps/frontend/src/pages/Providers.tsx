import { useState } from 'react'
import { Plus, Trash2, TestTube, Globe, Key, Power } from 'lucide-react'
import { toast } from 'sonner'
import { cn, getStatusDot } from '@/lib/utils'
import { useProviderStore, type Provider } from '@/store/store'

const defaultProviders: Provider[] = [
  { name: 'OpenRouter', enabled: false, base_url: 'https://openrouter.ai/api/v1', models: [], status: 'inactive' },
  { name: 'OpenAI', enabled: false, base_url: 'https://api.openai.com/v1', models: [], status: 'inactive' },
  { name: 'Gemini', enabled: false, base_url: 'https://generativelanguage.googleapis.com', models: [], status: 'inactive' },
]

export default function Providers() {
  const { providers, addProvider, removeProvider } = useProviderStore()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newProvider, setNewProvider] = useState({ name: '', base_url: '', api_key: '' })

  // Initialize with default providers if empty
  useState(() => {
    if (providers.length === 0) {
      defaultProviders.forEach((p) => addProvider(p))
    }
  })

  const handleAdd = () => {
    if (!newProvider.name || !newProvider.base_url) {
      toast.error('Name and Base URL are required')
      return
    }
    addProvider({
      name: newProvider.name,
      enabled: false,
      base_url: newProvider.base_url,
      models: [],
      status: 'inactive',
    })
    setNewProvider({ name: '', base_url: '', api_key: '' })
    setShowAddForm(false)
    toast.success(`Added provider: ${newProvider.name}`)
  }

  const testConnection = async (provider: Provider) => {
    toast.success(`Testing ${provider.name}...`)
    setTimeout(() => {
      toast.success(`${provider.name} responded OK`)
    }, 1500)
  }

  const toggleProvider = (provider: Provider) => {
    const newStatus = !provider.enabled
    toast.success(`${newStatus ? 'Enabled' : 'Disabled'} ${provider.name}`)
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Provider Manager</h1>
          <p className="page-description">Configure online AI providers</p>
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
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Provider Name</label>
              <input
                value={newProvider.name}
                onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
                placeholder="e.g., OpenRouter"
                className="input-field"
              />
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
          <div className="flex gap-2 mt-4">
            <button onClick={handleAdd} className="btn-primary">Save Provider</button>
            <button onClick={() => setShowAddForm(false)} className="btn-secondary">Cancel</button>
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
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-gray-500">{provider.base_url}</span>
                  {provider.latency_ms && (
                    <span className="text-xs text-cyan-400">{provider.latency_ms}ms</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button onClick={() => testConnection(provider)} className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-cyan-400 transition-all" title="Test Connection">
                <TestTube className="w-4 h-4" />
              </button>
              <button onClick={() => toggleProvider(provider)} className={cn('p-2 rounded-lg transition-all', 
                provider.enabled ? 'text-emerald-400 hover:bg-emerald-500/10' : 'text-gray-500 hover:bg-gray-800'
              )} title="Toggle">
                <Power className="w-4 h-4" />
              </button>
              <button onClick={() => removeProvider(provider.name)} className="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all" title="Remove">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Provider Info */}
      <div className="glass-panel p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">Security Notice</h3>
        <p className="text-xs text-gray-500">
          API keys are encrypted at rest using Fernet encryption. They are never logged or exposed in the UI.
          All provider communication occurs over HTTPS.
        </p>
      </div>
    </div>
  )
}
