import { useEffect, useState } from 'react'
import { Cpu, HardDrive, MemoryStick, Activity, Zap, Bot, Gauge, RefreshCw, Play, Square } from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiFetch } from '@/lib/utils'

interface Metrics {
  cpu_percent: number
  ram_percent: number
  ram_used_gb: number
  ram_total_gb: number
  gpu_percent: number | null
  vram_used_gb: number | null
  active_models: number
  active_mcps: number
  timestamp: string
}

export default function RuntimeMonitor() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [history, setHistory] = useState<number[]>([])
  const [isMonitoring, setIsMonitoring] = useState(false)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await apiFetch<Metrics>('/system/metrics')
        setMetrics(data)
        setHistory((prev) => [...prev.slice(-50), data.cpu_percent])
      } catch (err) {
        console.error('Failed to fetch metrics:', err)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 3000)
    return () => clearInterval(interval)
  }, [])

  const toggleMonitoring = async () => {
    try {
      if (isMonitoring) {
        await apiFetch('/runtime/monitoring/stop', { method: 'POST' })
        setIsMonitoring(false)
      } else {
        await apiFetch('/runtime/monitoring/start?interval=3', { method: 'POST' })
        setIsMonitoring(true)
      }
    } catch (err) {
      console.error('Toggle monitoring failed:', err)
    }
  }

  const gaugeColor = (value: number) => {
    if (value > 80) return 'text-red-400'
    if (value > 60) return 'text-yellow-400'
    return 'text-emerald-400'
  }

  const gaugeBgColor = (value: number) => {
    if (value > 80) return 'bg-red-500'
    if (value > 60) return 'bg-yellow-500'
    return 'bg-emerald-500'
  }

  const MetricGauge = ({ label, value, icon: Icon, color, unit, max = 100 }: any) => (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={cn('w-4 h-4', color)} />
          <span className="text-xs text-gray-500">{label}</span>
        </div>
        <span className={cn('text-lg font-bold', gaugeColor(value))}>
          {value}{unit}
        </span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', gaugeBgColor(value))}
          style={{ width: `${Math.min((value / max) * 100, 100)}%` }}
        />
      </div>
    </div>
  )

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Runtime Monitor</h1>
          <p className="page-description">Live system resource monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            {metrics && new Date(metrics.timestamp).toLocaleTimeString()}
          </span>
          <button
            onClick={toggleMonitoring}
            className={cn('flex items-center gap-2', isMonitoring ? 'btn-danger' : 'btn-primary')}
          >
            {isMonitoring ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isMonitoring ? 'Stop' : 'Monitor'}
          </button>
        </div>
      </div>

      {/* CPU Graph */}
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-medium text-gray-300">CPU Usage History</span>
          </div>
          <span className={cn('text-sm font-bold', gaugeColor(metrics?.cpu_percent || 0))}>
            {metrics?.cpu_percent.toFixed(1)}%
          </span>
        </div>
        <div className="h-24 flex items-end gap-0.5">
          {history.map((val, i) => (
            <div
              key={i}
              className={cn(
                'flex-1 rounded-t transition-all duration-300',
                val > 80 ? 'bg-red-500' : val > 60 ? 'bg-yellow-500' : 'bg-emerald-500'
              )}
              style={{ height: `${val}%`, opacity: 0.4 + (i / history.length) * 0.6 }}
            />
          ))}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricGauge
          label="CPU Usage"
          value={metrics?.cpu_percent || 0}
          icon={Cpu}
          color="text-cyan-400"
          unit="%"
        />
        <MetricGauge
          label="RAM Usage"
          value={metrics?.ram_percent || 0}
          icon={MemoryStick}
          color="text-emerald-400"
          unit="%"
        />
        <MetricGauge
          label="RAM Used"
          value={metrics?.ram_used_gb || 0}
          icon={HardDrive}
          color="text-purple-400"
          unit="GB"
          max={metrics?.ram_total_gb || 32}
        />
        <MetricGauge
          label="Active Models"
          value={metrics?.active_models || 0}
          icon={Bot}
          color="text-yellow-400"
          unit=""
          max={10}
        />
      </div>

      {/* GPU Info */}
      <div className="glass-card">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-medium text-gray-300">GPU Status</span>
        </div>
        {metrics?.gpu_percent !== null && metrics?.gpu_percent !== undefined ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">GPU Utilization</span>
              <span className="text-sm font-bold text-yellow-400">{metrics.gpu_percent}%</span>
            </div>
            {metrics.vram_used_gb && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">VRAM Used</span>
                <span className="text-sm font-bold text-purple-400">{metrics.vram_used_gb.toFixed(2)} GB</span>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-500">No GPU detected or GPU monitoring not available</p>
        )}
      </div>

      {/* Process Summary */}
      <div className="glass-card">
        <div className="flex items-center gap-2 mb-3">
          <Gauge className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-medium text-gray-300">Process Summary</span>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Active Models', value: metrics?.active_models || 0, color: 'text-emerald-400' },
            { label: 'Active MCPs', value: metrics?.active_mcps || 0, color: 'text-cyan-400' },
            { label: 'CPU Cores', value: 0, color: 'text-purple-400' },
          ].map((item) => (
            <div key={item.label} className="text-center">
              <div className={cn('text-2xl font-bold', item.color)}>{item.value}</div>
              <div className="text-xs text-gray-500 mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
