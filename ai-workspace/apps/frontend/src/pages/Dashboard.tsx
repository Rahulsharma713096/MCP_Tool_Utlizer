import { useEffect, useState } from 'react'import { Cpu, HardDrive, MemoryStick, Activity, Bot, Puzzle, Globe, Zap, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { apiFetch, cn } from '@/lib/utils'
import { useOllamaStore, useMCPStore, useProviderStore } from '@/store/store'

interface SystemInfo {
  cpus: number
  total_ram_gb: number
  available_ram_gb: number
  total_disk_gb: number
  free_disk_gb: number
  gpu_available: boolean
  gpu_name: string | null
}

interface HealthData {
  status: string
  ollama: boolean
  active_mcps: number
  active_providers: number
}

export default function Dashboard() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [health, setHealth] = useState<HealthData | null>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const { models } = useOllamaStore()
  const { mcps } = useMCPStore()
  const { providers } = useProviderStore()

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [info, healthData, metricsData] = await Promise.all([
          apiFetch<SystemInfo>('/system/info'),
          apiFetch<HealthData>('/health'),
          apiFetch<any>('/system/metrics'),
        ])
        setSystemInfo(info)
        setHealth(healthData)
        setMetrics(metricsData)
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const statCards = [
    {
      label: 'CPU Cores',
      value: systemInfo?.cpus || 0,
      icon: Cpu,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
    },
    {
      label: 'RAM',
      value: systemInfo ? `${(systemInfo.total_ram_gb - systemInfo.available_ram_gb).toFixed(1)}/${systemInfo.total_ram_gb} GB` : '—',
      icon: MemoryStick,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
    },
    {
      label: 'Disk',
      value: systemInfo ? `${(systemInfo.total_disk_gb - systemInfo.free_disk_gb).toFixed(0)}/${systemInfo.total_disk_gb} GB` : '—',
      icon: HardDrive,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    {
      label: 'CPU Usage',
      value: metrics ? `${metrics.cpu_percent.toFixed(1)}%` : '—',
      icon: Activity,
      color: metrics?.cpu_percent > 80 ? 'text-red-400' : 'text-emerald-400',
      bg: 'bg-emerald-500/10',
    },
  ]

  const moduleCards = [
    {
      label: 'Ollama Models',
      value: models.length,
      active: models.filter((m) => m.running).length,
      icon: Bot,
      color: 'text-emerald-400',
      path: 'ollama',
    },
    {
      label: 'MCP Servers',
      value: mcps.length,
      active: mcps.filter((m) => m.enabled).length,
      icon: Puzzle,
      color: 'text-cyan-400',
      path: 'mcp',
    },
    {
      label: 'Providers',
      value: providers.length,
      active: providers.filter((p) => p.enabled).length,
      icon: Globe,
      color: 'text-purple-400',
      path: 'providers',
    },
    {
      label: 'GPU',
      value: systemInfo?.gpu_available ? systemInfo.gpu_name || 'Available' : 'Not Available',
      active: systemInfo?.gpu_available ? 1 : 0,
      icon: Zap,
      color: 'text-yellow-400',
      path: 'runtime',
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gradient">AI Workspace Platform</h1>
        <p className="text-gray-500 mt-1">
          Enterprise AI Operations Control Center
        </p>
      </div>

      {/* Health Status */}
      {health && (
        <div className={cn(
          'flex items-center gap-3 px-4 py-3 rounded-xl border',
          health.status === 'healthy'
            ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
            : 'bg-yellow-500/5 border-yellow-500/20 text-yellow-400'
        )}>
          {health.status === 'healthy' ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : (
            <AlertTriangle className="w-5 h-5" />
          )}
          <span className="text-sm font-medium">
            System {health.status} • Ollama: {health.ollama ? 'Connected' : 'Not Detected'} • 
            {health.active_mcps} MCPs • {health.active_providers} Providers
          </span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="glass-card">
              <div className="flex items-start justify-between mb-3">
                <div className={cn('p-2 rounded-lg', card.bg)}>
                  <Icon className={cn('w-5 h-5', card.color)} />
                </div>
              </div>
              <div className="metric-value text-xl">{card.value}</div>
              <div className="metric-label mt-1">{card.label}</div>
            </div>
          )
        })}
      </div>

      {/* Module Cards */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Modules</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {moduleCards.map((card) => {
            const Icon = card.icon
            const activeCount = typeof card.active === 'number' ? card.active : 0
            return (
              <div key={card.label} className="glass-card cursor-pointer hover:border-gray-700">
                <div className="flex items-center gap-3 mb-3">
                  <Icon className={cn('w-5 h-5', card.color)} />
                  <span className="text-sm font-medium text-gray-300">{card.label}</span>
                </div>
                <div className="text-2xl font-bold text-gray-100">
                  {typeof card.value === 'number' ? card.value : card.value.split(' ')[0]}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all', card.color.replace('text', 'bg'))}
                      style={{ width: `${typeof card.value === 'number' && card.value > 0 ? (activeCount / (card.value as number)) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500">
                    {activeCount}/{card.value}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Start Chat', desc: 'Interact with AI models', page: 'chat', color: 'from-emerald-600 to-emerald-500' },
            { label: 'Manage Models', desc: 'Ollama runtime control', page: 'ollama', color: 'from-cyan-600 to-cyan-500' },
            { label: 'Configure MCP', desc: 'Plugin ecosystem', page: 'mcp', color: 'from-purple-600 to-purple-500' },
            { label: 'View Metrics', desc: 'System monitoring', page: 'runtime', color: 'from-orange-600 to-orange-500' },
          ].map((action) => (
            <button
              key={action.label}
              className={cn(
                'p-4 rounded-xl text-left text-white bg-gradient-to-br transition-all duration-200 hover:scale-[1.02] active:scale-95',
                action.color
              )}
            >
              <div className="font-semibold">{action.label}</div>
              <div className="text-xs text-white/70 mt-1">{action.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
