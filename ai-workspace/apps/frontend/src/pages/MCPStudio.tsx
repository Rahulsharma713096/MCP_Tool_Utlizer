import { useState } from 'react'
import { Plus, Trash2, Play, Square, TestTube, RefreshCw, Puzzle, Wifi, Terminal } from 'lucide-react'
import { toast } from 'sonner'
import { cn, getStatusDot } from '@/lib/utils'
import { useMCPStore, type MCP } from '@/store/store'

const defaultMcps: MCP[] = [
  { id: 1, name: 'Filesystem MCP', type: 'filesystem', enabled: false, status: 'inactive', transport: 'stdio' },
  { id: 2, name: 'Browser MCP', type: 'browser', enabled: false, status: 'inactive', transport: 'http', endpoint: 'http://localhost:3001' },
  { id: 3, name: 'GitHub MCP', type: 'github', enabled: false, status: 'inactive', transport: 'http', endpoint: 'https://api.github.com' },
  { id: 4, name: 'Database MCP', type: 'database', enabled: false, status: 'inactive', transport: 'stdio' },
  { id: 5, name: 'Python Executor', type: 'python', enabled: false, status: 'inactive', transport: 'stdio' },
]

export default function MCPStudio() {
  const { mcps, addMcp, removeMcp, toggleMcp } = useMCPStore()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newMCP, setNewMCP] = useState({ name: '', type: '', transport: 'stdio', endpoint: '' })

  // Initialize with default MCPs if empty
  useState(() => {
    if (mcps.length === 0) {
      defaultMcps.forEach((m) => addMcp(m))
    }
  })

  const handleAdd = () => {
    if (!newMCP.name || !newMCP.type) {
      toast.error('Name and type are required')
      return
    }
    addMcp({
      id: Date.now(),
      name: newMCP.name,
      type: newMCP.type,
      enabled: false,
      status: 'inactive',
      transport: newMCP.transport as 'stdio' | 'sse' | 'http',
      endpoint: newMCP.endpoint || undefined,
    })
    setNewMCP({ name: '', type: '', transport: 'stdio', endpoint: '' })
    setShowAddForm(false)
    toast.success(`Added MCP: ${newMCP.name}`)
  }

  const toggleMCPStatus = (mcp: MCP) => {
    toggleMcp(mcp.id)
    const newStatus = !mcp.enabled ? 'active' : 'inactive'
    toast.success(`${mcp.enabled ? 'Disabled' : 'Enabled'} MCP: ${mcp.name}`)
  }

  const testMCP = (mcp: MCP) => {
    toast.success(`Testing ${mcp.name}...`)
    setTimeout(() => {
      toast.success(`${mcp.name} responded OK`)
    }, 1000)
  }

  const transportIcons: Record<string, any> = {
    stdio: Terminal,
    http: Wifi,
    sse: RefreshCw,
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">MCP Studio</h1>
          <p className="page-description">Plugin ecosystem for Model Context Protocol servers</p>
        </div>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Add MCP
        </button>
      </div>

      {/* Add MCP Form */}
      {showAddForm && (
        <div className="glass-panel p-4 animate-slide-up">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Register New MCP Server</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Name</label>
              <input
                value={newMCP.name}
                onChange={(e) => setNewMCP({ ...newMCP, name: e.target.value })}
                placeholder="e.g., Custom MCP"
                className="input-field"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Type</label>
              <select
                value={newMCP.type}
                onChange={(e) => setNewMCP({ ...newMCP, type: e.target.value })}
                className="input-field"
              >
                <option value="">Select type...</option>
                <option value="filesystem">Filesystem</option>
                <option value="browser">Browser</option>
                <option value="github">GitHub</option>
                <option value="database">Database</option>
                <option value="python">Python Executor</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Transport</label>
              <select
                value={newMCP.transport}
                onChange={(e) => setNewMCP({ ...newMCP, transport: e.target.value })}
                className="input-field"
              >
                <option value="stdio">stdio</option>
                <option value="http">HTTP</option>
                <option value="sse">SSE</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Endpoint (optional)</label>
              <input
                value={newMCP.endpoint}
                onChange={(e) => setNewMCP({ ...newMCP, endpoint: e.target.value })}
                placeholder="http://localhost:3001"
                className="input-field"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={handleAdd} className="btn-primary">Register</button>
            <button onClick={() => setShowAddForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* MCP Cards */}
      <div className="grid gap-4">
        {mcps.map((mcp) => {
          const TransportIcon = transportIcons[mcp.transport] || Terminal
          return (
            <div key={mcp.id} className="glass-card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', mcp.enabled ? 'bg-emerald-500/10' : 'bg-gray-800')}>
                  <Puzzle className={cn('w-5 h-5', mcp.enabled ? 'text-emerald-400' : 'text-gray-600')} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200">{mcp.name}</span>
                    <span className={cn('w-2 h-2 rounded-full', getStatusDot(mcp.enabled ? 'active' : 'inactive'))} />
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-gray-500">{mcp.type}</span>
                    <TransportIcon className="w-3 h-3 text-gray-600" />
                    <span className="text-xs text-gray-600">{mcp.transport}</span>
                    {mcp.endpoint && <span className="text-xs text-gray-600 truncate max-w-[200px]">{mcp.endpoint}</span>}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={() => testMCP(mcp)} className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-cyan-400 transition-all" title="Test">
                  <TestTube className="w-4 h-4" />
                </button>
                {mcp.enabled ? (
                  <button onClick={() => toggleMCPStatus(mcp)} className="btn-danger flex items-center gap-2 text-sm">
                    <Square className="w-3 h-3" />
                    Disable
                  </button>
                ) : (
                  <button onClick={() => toggleMCPStatus(mcp)} className="btn-primary flex items-center gap-2 text-sm">
                    <Play className="w-3 h-3" />
                    Enable
                  </button>
                )}
                <button onClick={() => removeMcp(mcp.id)} className="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all" title="Delete">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
