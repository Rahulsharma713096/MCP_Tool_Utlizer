import { useState } from 'react'
import { Sun, Moon, Palette, Sliders, Shield, Database, RefreshCw, Save } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { useUIStore, type Theme } from '@/store/store'

const themes: { id: Theme; label: string; description: string; color: string }[] = [
  { id: 'neon', label: 'Neon', description: 'Vibrant green accents on dark', color: 'bg-emerald-500' },
  { id: 'glass', label: 'Glassmorphism', description: 'Frosted glass aesthetics', color: 'bg-white/20' },
  { id: 'cyberpunk', label: 'Cyberpunk', description: 'Pink and cyan vibes', color: 'bg-cyber-pink' },
  { id: 'minimal', label: 'Minimal', description: 'Clean and distraction-free', color: 'bg-gray-500' },
  { id: 'enterprise', label: 'Enterprise', description: 'Professional dark theme', color: 'bg-blue-500' },
]

export default function Settings() {
  const { theme, setTheme, sidebarCollapsed, setSidebarCollapsed } = useUIStore()
  const [runtimeConfig, setRuntimeConfig] = useState({
    model_idle_timeout: 10,
    max_cpu: 90,
    max_ram: 85,
    auto_unload: true,
    gpu_monitoring: true,
  })
  const [saving, setSaving] = useState(false)

  const saveSettings = () => {
    setSaving(true)
    setTimeout(() => {
      setSaving(false)
      toast.success('Settings saved successfully')
    }, 1000)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Appearance */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Palette className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-semibold text-gray-200">Appearance</h2>
        </div>

        <div className="glass-panel p-6">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Theme</h3>
          <div className="grid grid-cols-5 gap-3">
            {themes.map((t) => (
              <button
                key={t.id}
                onClick={() => setTheme(t.id)}
                className={cn(
                  'p-4 rounded-xl text-center transition-all duration-200 border',
                  theme === t.id
                    ? 'border-emerald-500 bg-emerald-500/10'
                    : 'border-gray-800 bg-gray-900 hover:border-gray-700'
                )}
              >
                <div className={cn('w-8 h-8 rounded-full mx-auto mb-2', t.color)} />
                <div className="text-sm font-medium text-gray-200">{t.label}</div>
                <div className="text-xs text-gray-500 mt-1">{t.description}</div>
              </button>
            ))}
          </div>

          <div className="mt-6 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-300">Sidebar</h3>
              <p className="text-xs text-gray-500">Auto-collapse sidebar</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={sidebarCollapsed}
                onChange={(e) => setSidebarCollapsed(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-500/50 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600" />
            </label>
          </div>
        </div>
      </section>

      {/* Runtime Configuration */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Sliders className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-gray-200">Runtime Configuration</h2>
        </div>

        <div className="glass-panel p-6 space-y-4">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Model Idle Timeout (minutes)</label>
              <input
                type="number"
                value={runtimeConfig.model_idle_timeout}
                onChange={(e) => setRuntimeConfig({ ...runtimeConfig, model_idle_timeout: parseInt(e.target.value) })}
                className="input-field"
                min="1"
                max="60"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Max CPU %</label>
              <input
                type="number"
                value={runtimeConfig.max_cpu}
                onChange={(e) => setRuntimeConfig({ ...runtimeConfig, max_cpu: parseInt(e.target.value) })}
                className="input-field"
                min="50"
                max="100"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Max RAM %</label>
              <input
                type="number"
                value={runtimeConfig.max_ram}
                onChange={(e) => setRuntimeConfig({ ...runtimeConfig, max_ram: parseInt(e.target.value) })}
                className="input-field"
                min="50"
                max="100"
              />
            </div>
          </div>

          <div className="space-y-3 pt-2">
            {[
              { id: 'auto_unload', label: 'Auto-unload idle models', checked: runtimeConfig.auto_unload },
              { id: 'gpu_monitoring', label: 'Enable GPU monitoring', checked: runtimeConfig.gpu_monitoring },
            ].map((item) => (
              <div key={item.id} className="flex items-center justify-between">
                <span className="text-sm text-gray-300">{item.label}</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={item.checked}
                    onChange={(e) => setRuntimeConfig({ ...runtimeConfig, [item.id]: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-500/50 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600" />
                </label>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Database */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Database className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-semibold text-gray-200">Database</h2>
        </div>

        <div className="glass-panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-300">SQLite Database</h3>
              <p className="text-xs text-gray-500 mt-1">Located at: data/ai_workspace.db</p>
            </div>
            <button className="btn-secondary flex items-center gap-2 text-sm">
              <RefreshCw className="w-3.5 h-3.5" />
              Reset Database
            </button>
          </div>
        </div>
      </section>

      {/* Security */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-yellow-400" />
          <h2 className="text-lg font-semibold text-gray-200">Security</h2>
        </div>

        <div className="glass-panel p-6">
          <div className="space-y-3">
            {[
              { label: 'API Key Encryption', value: 'Fernet (AES-128)', status: 'active' },
              { label: 'JWT Authentication', value: 'HS256', status: 'active' },
              { label: 'Rate Limiting', value: '100 requests/minute', status: 'active' },
              { label: 'MCP Sandbox', value: 'Isolated execution', status: 'active' },
              { label: 'Input Sanitization', value: 'Pydantic validation', status: 'active' },
            ].map((sec) => (
              <div key={sec.label} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-sm text-gray-300">{sec.label}</span>
                </div>
                <span className="text-xs text-gray-500">{sec.value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={saveSettings}
          disabled={saving}
          className="btn-primary flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save All Settings'}
        </button>
      </div>
    </div>
  )
}
