import { useState, useEffect } from 'react'
import { ScrollText, Filter, Download, Trash2, RefreshCw, AlertTriangle, Info, Bug, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LogEntry {
  timestamp: string
  level: string
  message: string
  module: string
}

const logLevels = ['ALL', 'INFO', 'WARNING', 'ERROR', 'DEBUG']

const mockLogs: LogEntry[] = [
  { timestamp: new Date().toISOString(), level: 'INFO', message: 'System started successfully', module: 'system' },
  { timestamp: new Date(Date.now() - 1000).toISOString(), level: 'INFO', message: 'API server listening on port 8000', module: 'api' },
  { timestamp: new Date(Date.now() - 2000).toISOString(), level: 'INFO', message: 'Database connection established', module: 'database' },
  { timestamp: new Date(Date.now() - 3000).toISOString(), level: 'WARNING', message: 'Ollama not detected on system', module: 'ollama' },
  { timestamp: new Date(Date.now() - 4000).toISOString(), level: 'INFO', message: 'WebSocket server ready', module: 'websocket' },
  { timestamp: new Date(Date.now() - 5000).toISOString(), level: 'INFO', message: 'Runtime monitor started (interval: 5s)', module: 'runtime' },
  { timestamp: new Date(Date.now() - 6000).toISOString(), level: 'DEBUG', message: 'Loading configuration from configs/', module: 'config' },
  { timestamp: new Date(Date.now() - 7000).toISOString(), level: 'INFO', message: 'MCP Registry initialized with 5 servers', module: 'mcp' },
  { timestamp: new Date(Date.now() - 8000).toISOString(), level: 'INFO', message: 'Provider abstraction layer ready', module: 'provider' },
  { timestamp: new Date(Date.now() - 9000).toISOString(), level: 'INFO', message: 'UI settings loaded', module: 'ui' },
]

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>(mockLogs)
  const [filter, setFilter] = useState('ALL')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(() => {
      const levels = ['INFO', 'INFO', 'INFO', 'WARNING', 'DEBUG']
      const modules = ['system', 'api', 'runtime', 'mcp', 'monitor']
      const newLog: LogEntry = {
        timestamp: new Date().toISOString(),
        level: levels[Math.floor(Math.random() * levels.length)],
        message: `Runtime heartbeat - System healthy`,
        module: modules[Math.floor(Math.random() * modules.length)],
      }
      setLogs((prev) => [...prev.slice(-100), newLog])
    }, 5000)
    return () => clearInterval(interval)
  }, [autoRefresh])

  const filteredLogs = logs.filter((log) => {
    if (filter !== 'ALL' && log.level !== filter) return false
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  }).reverse()

  const levelIcon = (level: string) => {
    switch (level) {
      case 'ERROR': return <XCircle className="w-3.5 h-3.5 text-red-400" />
      case 'WARNING': return <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
      case 'INFO': return <Info className="w-3.5 h-3.5 text-blue-400" />
      case 'DEBUG': return <Bug className="w-3.5 h-3.5 text-purple-400" />
      default: return <Info className="w-3.5 h-3.5 text-gray-400" />
    }
  }

  const levelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'text-red-400 bg-red-500/10'
      case 'WARNING': return 'text-yellow-400 bg-yellow-500/10'
      case 'INFO': return 'text-blue-400 bg-blue-500/10'
      case 'DEBUG': return 'text-purple-400 bg-purple-500/10'
      default: return 'text-gray-400 bg-gray-500/10'
    }
  }

  return (
    <div className="space-y-4 animate-fade-in h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="page-title">System Logs</h1>
          <p className="page-description">Real-time system event log stream</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn('btn-secondary flex items-center gap-2 text-sm', autoRefresh && 'bg-emerald-600/20 border-emerald-500/30 text-emerald-400')}
          >
            <RefreshCw className={cn('w-3.5 h-3.5', autoRefresh && 'animate-spin')} />
            Auto
          </button>
          <button onClick={() => setLogs(mockLogs)} className="btn-secondary flex items-center gap-2 text-sm">
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex gap-1">
          {logLevels.map((level) => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                filter === level
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              )}
            >
              {level}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search logs..."
          className="input-field text-sm py-1.5 w-48"
        />
        <span className="text-xs text-gray-600">{filteredLogs.length} entries</span>
      </div>

      {/* Log Stream */}
      <div className="flex-1 glass-panel overflow-hidden">
        <div className="h-full overflow-y-auto p-2 font-mono text-xs">
          {filteredLogs.map((log, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 px-3 py-1.5 hover:bg-gray-800/30 rounded transition-colors"
            >
              <span className="text-gray-600 whitespace-nowrap shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={cn('badge px-1.5 py-0.5 text-[10px] shrink-0', levelColor(log.level))}>
                {log.level}
              </span>
              <span className="text-gray-600 shrink-0 w-16">{log.module}</span>
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
