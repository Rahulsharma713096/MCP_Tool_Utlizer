import { useState, useEffect, useRef } from 'react'
import { Plus, Trash2, Play, Square, TestTube, RefreshCw, Puzzle, Wifi, Terminal, Code, Copy, CheckCircle2, ChevronDown, ChevronUp, AlertTriangle, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { cn, getStatusDot } from '@/lib/utils'
import { useMCPStore, type MCP } from '@/store/store'

const defaultMcps: MCP[] = [
  { id: 1, name: 'Filesystem MCP', type: 'filesystem', enabled: false, status: 'inactive', transport: 'stdio', directory: './workspace', command: 'npx', args: ['-y', '@modelcontextprotocol/server-filesystem', './workspace'] },
  { id: 2, name: 'Browser MCP', type: 'browser', enabled: false, status: 'inactive', transport: 'http', endpoint: 'http://localhost:3001' },
  { id: 3, name: 'GitHub MCP', type: 'github', enabled: false, status: 'inactive', transport: 'http', endpoint: 'https://api.github.com' },
  { id: 4, name: 'Database MCP', type: 'database', enabled: false, status: 'inactive', transport: 'http', endpoint: 'http://localhost:5432' },
  { id: 5, name: 'Playwright MCP', type: 'browser', enabled: false, status: 'inactive', transport: 'http', endpoint: 'http://localhost:3002' },
  { id: 6, name: 'Python Executor', type: 'python', enabled: false, status: 'inactive', transport: 'http', endpoint: 'http://localhost:8080' },
]

function ManualSetupGuide() {
  const [expanded, setExpanded] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const copyToClipboard = async (json: string, id: string) => {
    try {
      await navigator.clipboard.writeText(json)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {
      // Fallback
      const textarea = document.createElement('textarea')
      textarea.value = json
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    }
  }

  return (
    <div className="glass-panel overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10">
            <Code className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-gray-200">Manual MCP Setup</h3>
            <p className="text-xs text-gray-500 mt-0.5">Quick-add popular MCP servers via npx — copy from the community</p>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 animate-slide-up">
          <p className="text-xs text-gray-500 mb-4 leading-relaxed">
            You can manually add any MCP server by pasting the <code className="text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded text-[11px]">npx</code> command JSON from the MCP community.
            Copy the JSON below and register a new MCP server with these settings, or paste the exact config into your MCP settings file.
          </p>

          <div className="space-y-3">
            {MANUAL_SETUP_EXAMPLES.map((mcp) => {
              const configJson = JSON.stringify({
                name: mcp.name,
                type: mcp.type,
                transport: mcp.transport,
                command: mcp.command,
                args: mcp.args,
              }, null, 2)
              return (
                <div key={mcp.name} className="rounded-lg border border-gray-800 bg-gray-900/50">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200">{mcp.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">{mcp.type}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-600">{mcp.command} {mcp.args?.join(' ')}</span>
                      <button
                        onClick={() => copyToClipboard(configJson, mcp.name)}
                        className="p-1.5 rounded-md hover:bg-gray-800 transition-colors"
                        title="Copy config JSON"
                      >
                        {copiedId === mcp.name ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5 text-gray-500" />
                        )}
                      </button>
                    </div>
                  </div>
                  <pre className="p-3 text-[11px] font-mono text-gray-400 overflow-x-auto">
                    <code>{configJson}</code>
                  </pre>
                </div>
              )
            })}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
            <p className="text-xs text-emerald-300/80">
              <strong className="text-emerald-400">Tip:</strong> After copying the JSON, click <strong>"Add MCP"</strong> above and enter the name, type, and command manually.
              For production, add these to your <code className="text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded text-[11px]">mcp_config.json</code> file.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

const MANUAL_SETUP_EXAMPLES = [
  {
    name: 'Playwright MCP',
    type: 'browser',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', '@playwright/mcp'],
    description: 'Browser automation via Playwright',
  },
  {
    name: 'SQLite MCP',
    type: 'database',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', '@anthropic/mcp-sqlite', '--db', './data.db'],
    description: 'Database access via natural language',
  },
  {
    name: 'GitHub MCP',
    type: 'github',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/github'],
    description: 'GitHub API integration',
  },
  {
    name: 'Filesystem MCP',
    type: 'filesystem',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/filesystem', './workspace'],
    description: 'File system access and management',
  },
  {
    name: 'Memory MCP',
    type: 'custom',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', '@anthropic/mcp-memory'],
    description: 'Persistent memory and knowledge graph',
  },
]

// Quick JSON templates for the Custom JSON textarea in the Add MCP form
const CUSTOM_JSON_TEMPLATES = [
  {
    icon: '🎭',
    label: 'Playwright',
    description: 'Browser automation via Playwright MCP',
    json: {
      name: 'Playwright MCP',
      type: 'browser',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@playwright/mcp'],
    },
  },
  {
    icon: '🗄️',
    label: 'SQLite',
    description: 'Database access via natural language',
    json: {
      name: 'SQLite MCP',
      type: 'database',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@anthropic/mcp-sqlite', '--db', './data.db'],
    },
  },
  {
    icon: '🐙',
    label: 'GitHub',
    description: 'GitHub API integration',
    json: {
      name: 'GitHub MCP',
      type: 'github',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/github'],
    },
  },
  {
    icon: '📁',
    label: 'Filesystem',
    description: 'File system access and management',
    json: {
      name: 'Filesystem MCP',
      type: 'filesystem',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', './workspace'],
      directory: './workspace',
    },
  },
  {
    icon: '🧠',
    label: 'Memory',
    description: 'Persistent memory and knowledge graph',
    json: {
      name: 'Memory MCP',
      type: 'custom',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@anthropic/mcp-memory'],
    },
  },
  {
    icon: '🔧',
    label: 'Custom env',
    description: 'Custom MCP with environment variables',
    json: {
      name: 'Custom MCP',
      type: 'custom',
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@owner/my-package'],
      env: { API_KEY: 'your-key', DEBUG: 'true' },
    },
  },
]

export default function MCPStudio() {
  const { mcps, addMcp, removeMcp, toggleMcp } = useMCPStore()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newMCP, setNewMCP] = useState({ name: '', type: '', transport: 'stdio', endpoint: '', directory: './workspace', github_repo: '', github_ref: 'main', root: '', exclude: '', customJson: '' })
  const [showGitHubForm, setShowGitHubForm] = useState(false)
  const [showCustomJson, setShowCustomJson] = useState(false)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [jsonValidation, setJsonValidation] = useState<{ status: 'idle' | 'valid' | 'invalid' | 'missing_fields'; message?: string; fields?: Record<string, any> }>({ status: 'idle' })
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced JSON validation as user types
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (!newMCP.customJson?.trim()) {
      setJsonValidation({ status: 'idle' })
      return
    }

    debounceRef.current = setTimeout(() => {
      try {
        const parsed = JSON.parse(newMCP.customJson)
        if (!parsed.name || !parsed.type) {
          setJsonValidation({ status: 'missing_fields', message: 'Missing required fields: "name" and "type"', fields: parsed })
        } else {
          setJsonValidation({ status: 'valid', fields: parsed })
        }
      } catch (e) {
        setJsonValidation({ status: 'invalid', message: (e as Error).message })
      }
    }, 400)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [newMCP.customJson])

  // Initialize with default MCPs if empty
  useState(() => {
    if (mcps.length === 0) {
      defaultMcps.forEach((m) => addMcp(m))
    }
  })

  const handleAdd = () => {        // Custom JSON mode: parse JSON and create MCP from parsed fields
    if (showCustomJson) {
      if (!newMCP.customJson?.trim()) {
        setJsonError('JSON is empty — adding with minimal config')
        // Default to HTTP transport so enable always works (marks as configured)
        const mcpConfig: MCP = {
          id: Date.now(),
          name: 'Unnamed MCP',
          type: 'custom',
          enabled: false,
          status: 'inactive',
          transport: 'http',
          endpoint: 'http://localhost:3000',
        }
        addMcp(mcpConfig)
        resetForm()
        toast.warning('Added MCP with HTTP transport — JSON was empty')
        return
      }
      try {
        const parsed = JSON.parse(newMCP.customJson)
        const transport = parsed.transport || 'http'
        const mcpConfig: MCP = {
          id: Date.now(),
          name: parsed.name || 'Unnamed MCP',
          type: parsed.type || 'custom',
          enabled: false,
          status: 'inactive',
          transport: transport,
          command: parsed.command || undefined,
          args: parsed.args || undefined,
          endpoint: parsed.endpoint || undefined,
          directory: parsed.directory || undefined,
          github_repo: parsed.github_repo || undefined,
          github_ref: parsed.github_ref || undefined,
          root: parsed.root || undefined,
          exclude: parsed.exclude || undefined,
          env: parsed.env || undefined,
        }
        addMcp(mcpConfig)
        resetForm()
        if (!parsed.name || !parsed.type) {
          toast.warning('Added MCP — missing "name" or "type", using defaults')
        } else {
          toast.success(`Added MCP: ${parsed.name}`)
        }
        return
      } catch (e) {
        // JSON is invalid — add what we can, default to HTTP transport
        setJsonError(`Invalid JSON: ${(e as Error).message}`)
        const mcpConfig: MCP = {
          id: Date.now(),
          name: 'Invalid JSON MCP',
          type: 'custom',
          enabled: false,
          status: 'inactive',
          transport: 'http',
          endpoint: 'http://localhost:3000',
        }
        addMcp(mcpConfig)
        resetForm()
        toast.warning('Added MCP with HTTP transport — JSON had syntax errors')
        return
      }
    }

    // Normal form mode
    if (!newMCP.name || !newMCP.type) {
      toast.error('Name and type are required')
      return
    }
    
    const mcpConfig: MCP = {
      id: Date.now(),
      name: newMCP.name,
      type: newMCP.type,
      enabled: false,
      status: 'inactive',
      transport: newMCP.transport as 'stdio' | 'sse' | 'http',
      endpoint: newMCP.endpoint || undefined,
    }

    // Filesystem MCP: configure directory access
    if (newMCP.type === 'filesystem') {
      const dir = newMCP.directory || './workspace'
      mcpConfig.directory = dir
      mcpConfig.command = 'npx'
      mcpConfig.args = ['-y', '@modelcontextprotocol/server-filesystem', dir]
    }

    // Add GitHub repo configuration if provided
    if (newMCP.github_repo) {
      mcpConfig.github_repo = newMCP.github_repo
      mcpConfig.github_ref = newMCP.github_ref || 'main'
      mcpConfig.root = newMCP.root || undefined
      mcpConfig.exclude = newMCP.exclude
        ? newMCP.exclude.split('\n').map((s) => s.trim()).filter(Boolean)
        : undefined
      // Auto-detect command for npx-based MCPs
      mcpConfig.command = 'npx'
      const repoParts = newMCP.github_repo.split('/')
      const packageName = repoParts.length >= 2 ? `@${repoParts[0]}/${repoParts[1]}` : repoParts[0]
      mcpConfig.args = ['-y', packageName]
    }

    addMcp(mcpConfig)
    resetForm()
    toast.success(`Added MCP: ${newMCP.name}`)
  }

  const resetForm = () => {
    setNewMCP({ name: '', type: '', transport: 'stdio', endpoint: '', directory: './workspace', github_repo: '', github_ref: 'main', root: '', exclude: '', customJson: '' })
    setShowAddForm(false)
    setShowGitHubForm(false)
    setShowCustomJson(false)
    setJsonError(null)
    setJsonValidation({ status: 'idle' })
  }

  const toggleMCPStatus = async (mcp: MCP) => {
    toggleMcp(mcp.id)
    const wasEnabled = mcp.enabled

    if (wasEnabled) {
      // Disable: stop the MCP server via API
      try {
        const res = await fetch(`/api/v1/mcps/${mcp.id}/disable`, { method: 'POST' })
        const data = await res.json()
        toast.success(`Disabled MCP: ${mcp.name}`)
      } catch (err) {
        toast.error(`Failed to disable: ${err}`)
        toggleMcp(mcp.id) // revert
      }
    } else {
      // Enable: start the MCP server via API with full config
      try {
        // For HTTP/SSE transport: only send transport and endpoint — no command/args
        const isHttpMCP = mcp.transport === 'http' || mcp.transport === 'sse'
        const enableBody: Record<string, any> = {
          name: mcp.name,
          type: mcp.type,
          transport: mcp.transport,
          endpoint: mcp.endpoint || null,
        }
        if (!isHttpMCP) {
          enableBody.command = mcp.command || 'npx'
          enableBody.args = mcp.args || (mcp.type === 'filesystem'
            ? ['-y', '@modelcontextprotocol/server-filesystem', mcp.directory || './workspace']
            : undefined)
        }

        const res = await fetch(`/api/v1/mcps/${mcp.id}/enable`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(enableBody),
        })
        const data = await res.json()
        if (data.status === 'started' || data.status === 'already_running') {
          toast.success(`Enabled MCP: ${mcp.name}${data.pid ? ` (PID: ${data.pid})` : ''}`)
          if (data.warning) {
            toast.warning(data.warning)
          }
        } else {
          toast.error(`Failed to enable: ${data.message || 'Unknown error'}`)
          toggleMcp(mcp.id) // revert
        }
      } catch (err) {
        toast.error(`Failed to enable: ${err}`)
        toggleMcp(mcp.id) // revert
      }
    }
  }

  const testMCP = async (mcp: MCP) => {
    toast.success(`Testing ${mcp.name}...`)
    try {
      const res = await fetch(`/api/v1/mcps/${mcp.id}/test`)
      const data = await res.json()
      if (data.status === 'healthy') {
        toast.success(`${mcp.name} responded OK`)
      } else if (data.status === 'inactive') {
        toast.warning(`${mcp.name} is inactive (enable it first)`)
      } else {
        toast.error(`${mcp.name}: ${data.status}`)
      }
    } catch (err) {
      toast.error(`Test failed: ${err}`)
    }
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
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Register New MCP Server</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setShowCustomJson(false)
                  setShowGitHubForm(!showGitHubForm)
                  if (!showGitHubForm) {
                    setNewMCP({ ...newMCP, type: 'github', transport: 'stdio' })
                  }
                }}
                className={cn(
                  'btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5',
                  showGitHubForm && !showCustomJson && 'bg-emerald-600/20 border-emerald-500/30 text-emerald-400'
                )}
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                </svg>
                {showGitHubForm && !showCustomJson ? 'Simple Form' : 'GitHub Repo'}
              </button>
              <button
                onClick={() => {
                  setShowGitHubForm(false)
                  setShowCustomJson(!showCustomJson)
                }}
                className={cn(
                  'btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5',
                  showCustomJson && 'bg-amber-600/20 border-amber-500/30 text-amber-400'
                )}
              >
                <Code className="w-3.5 h-3.5" />
                {showCustomJson ? 'Simple Form' : 'Custom JSON'}
              </button>
            </div>
          </div>

          {showCustomJson ? (
            <>
              <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/10 mb-4">
                <p className="text-xs text-amber-300/80">
                  <strong className="text-amber-400">Custom JSON Configuration</strong> — Paste the full MCP server
                  configuration as JSON. All fields (name, type, command, args, transport, etc.) are parsed automatically.
                </p>
              </div>

              {/* Preset Template Buttons */}
              <div className="mb-3">
                <label className="text-xs text-gray-500 block mb-1.5">Quick Templates</label>
                <div className="flex flex-wrap gap-1.5">
                  {CUSTOM_JSON_TEMPLATES.map((template) => (
                    <button
                      key={template.label}
                      onClick={() => {
                        setNewMCP({ ...newMCP, customJson: JSON.stringify(template.json, null, 2) })
                        setJsonError(null)
                        setJsonValidation({ status: 'valid', fields: template.json })
                      }}
                      className="px-2.5 py-1 text-xs rounded-lg border border-gray-700 bg-gray-800/50 hover:bg-gray-700/50 hover:border-gray-600 text-gray-300 hover:text-gray-100 transition-all active:scale-95"
                      title={template.description}
                    >
                      {template.icon} {template.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-500 block mb-1">
                  MCP JSON Configuration{' '}
                  <span className="text-gray-600">(required: name, type)</span>
                </label>
                <textarea
                  value={newMCP.customJson}
                  onChange={(e) => {
                    setNewMCP({ ...newMCP, customJson: e.target.value })
                    setJsonError(null)
                  }}
                  placeholder={`{
  "name": "My Custom MCP",
  "type": "custom",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@owner/my-package"],
  "env": {
    "API_KEY": "your-key"
  }
}`}
                  rows={12}
                  className={cn(
                    'input-field resize-none font-mono text-xs w-full',
                    jsonValidation.status === 'invalid' && 'border-red-500/50',
                    jsonValidation.status === 'valid' && 'border-emerald-500/30',
                  )}
                  spellCheck={false}
                />

                {/* Real-time Validation Feedback */}
                <div className="mt-2 space-y-2">
                  {/* Idle state — empty textarea */}
                  {jsonValidation.status === 'idle' && !newMCP.customJson?.trim() && (
                    <p className="text-[11px] text-gray-600 flex items-center gap-1.5">
                      <Code className="w-3 h-3" />
                      Paste a JSON configuration or use a template above
                    </p>
                  )}

                  {/* Invalid JSON — parse error */}
                  {jsonValidation.status === 'invalid' && (
                    <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20">
                      <p className="text-xs text-red-400 flex items-start gap-1.5">
                        <XCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                        <span>
                          <strong>Invalid JSON:</strong> {jsonValidation.message}
                        </span>
                      </p>
                    </div>
                  )}

                  {/* Valid JSON but missing required fields */}
                  {jsonValidation.status === 'missing_fields' && jsonValidation.fields && (
                    <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <p className="text-xs text-amber-400 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        {jsonValidation.message}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {Object.entries(jsonValidation.fields).map(([key, value]) => (
                          <span key={key} className="px-1.5 py-0.5 text-[10px] rounded bg-gray-800/80 text-gray-500">
                            <span className="text-gray-600">{key}:</span>{' '}
                            <span className={cn(key === 'name' || key === 'type' ? (!value ? 'text-red-400' : 'text-emerald-400') : 'text-cyan-400')}>
                              {value ? (typeof value === 'string' ? `"${value}"` : JSON.stringify(value)) : '⚠️ missing'}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Fully valid JSON with all required fields */}
                  {jsonValidation.status === 'valid' && jsonValidation.fields && (
                    <>
                      <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <p className="text-xs text-emerald-400 flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          Valid JSON — all required fields present. Ready to register.
                        </p>
                      </div>
                      {/* Parsed Fields Preview Card */}
                      <div className="p-3 rounded-lg bg-gray-800/40 border border-gray-700/50">
                        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">
                          <Code className="w-3 h-3 inline mr-1 -mt-0.5" />
                          Parsed Fields Preview
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.entries(jsonValidation.fields).map(([key, value]) => (
                            <span key={key} className="px-2 py-0.5 text-[11px] rounded bg-gray-800 border border-gray-700 text-gray-400">
                              <span className="text-gray-500">{key}:</span>{' '}
                              <span className={cn(
                                key === 'name' ? 'text-white' :
                                key === 'type' ? 'text-sky-400' :
                                key === 'command' ? 'text-purple-400' :
                                'text-cyan-400'
                              )}>
                                {typeof value === 'string' ? `"${value}"` : Array.isArray(value) ? `[${value.length} items]` : JSON.stringify(value)}
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </>
          ) : showGitHubForm ? (
            <>
              <div className="p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/10 mb-4">
                <p className="text-xs text-cyan-300/80">
                  <strong className="text-cyan-400">GitHub MCP Service</strong> — Configure an npx-based MCP server
                  from a GitHub repository. This will automatically set up the command and arguments.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500 block mb-1">Name</label>
                  <input
                    value={newMCP.name}
                    onChange={(e) => setNewMCP({ ...newMCP, name: e.target.value })}
                    placeholder="e.g., my-service"
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
                <div className="col-span-2">
                  <label className="text-xs text-gray-500 block mb-1">
                    GitHub Repository <span className="text-gray-600">(owner/repo)</span>
                  </label>
                  <input
                    value={newMCP.github_repo}
                    onChange={(e) => setNewMCP({ ...newMCP, github_repo: e.target.value })}
                    placeholder="e.g., owner/my-service"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">
                    Git Ref <span className="text-gray-600">(optional, default: main)</span>
                  </label>
                  <input
                    value={newMCP.github_ref}
                    onChange={(e) => setNewMCP({ ...newMCP, github_ref: e.target.value })}
                    placeholder="main"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 block mb-1">
                    Root Directory <span className="text-gray-600">(optional)</span>
                  </label>
                  <input
                    value={newMCP.root}
                    onChange={(e) => setNewMCP({ ...newMCP, root: e.target.value })}
                    placeholder="src/main/java"
                    className="input-field"
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-xs text-gray-500 block mb-1">
                    Exclude Patterns <span className="text-gray-600">(one per line, optional)</span>
                  </label>
                  <textarea
                    value={newMCP.exclude}
                    onChange={(e) => setNewMCP({ ...newMCP, exclude: e.target.value })}
                    placeholder={`**/vendor/**\n**/node_modules/**`}
                    rows={3}
                    className="input-field resize-none"
                  />
                </div>
              </div>
            </>
          ) : (
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
                  onChange={(e) => setNewMCP({
                    ...newMCP,
                    type: e.target.value,
                    // Default directory for filesystem type
                    directory: e.target.value === 'filesystem' ? (newMCP.directory || './workspace') : newMCP.directory,
                  })}
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
              {newMCP.type === 'filesystem' && (
                <div className="col-span-2">
                  <label className="text-xs text-gray-500 block mb-1">
                    Allowed Directory <span className="text-gray-600">(the AI can access this folder and its children)</span>
                  </label>
                  <input
                    value={newMCP.directory}
                    onChange={(e) => setNewMCP({ ...newMCP, directory: e.target.value })}
                    placeholder="./workspace"
                    className="input-field font-mono text-xs"
                  />
                  <p className="text-xs text-gray-600 mt-1">
                    The filesystem MCP server uses{' '}
                    <code className="text-cyan-400 bg-cyan-500/10 px-1 py-0.5 rounded text-[11px]">npx -y @modelcontextprotocol/server-filesystem</code>
                    {' '}to allow AI read/write access to the specified directory.
                  </p>
                </div>
              )}
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
          )}

          <div className="flex gap-2 mt-4">
            <button onClick={handleAdd} className="btn-primary">Register</button>
            <button onClick={resetForm} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {/* Manual MCP Setup Guide */}
      <ManualSetupGuide />

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
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-200 truncate">{mcp.name}</span>
                    <span className={cn('w-2 h-2 rounded-full', getStatusDot(mcp.enabled ? 'active' : 'inactive'))} />
                  </div>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <span className="text-xs text-gray-500">{mcp.type}</span>
                    <TransportIcon className="w-3 h-3 text-gray-600" />
                    <span className="text-xs text-gray-600">{mcp.transport}</span>
                    {mcp.endpoint && <span className="text-xs text-gray-600 truncate max-w-[150px]">{mcp.endpoint}</span>}
                    {mcp.directory && mcp.type === 'filesystem' && (
                      <span className="text-xs text-amber-400/80 truncate max-w-[200px]" title={`Allowed directory: ${mcp.directory}`}>
                        📁 {mcp.directory}
                      </span>
                    )}
                    {mcp.github_repo && (
                      <span className="text-xs text-cyan-400/80 truncate max-w-[200px]" title={`GitHub: ${mcp.github_repo} (${mcp.github_ref || 'main'})`}>
                        <svg className="w-3 h-3 inline mr-1 -mt-0.5" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                        </svg>
                        {mcp.github_repo}@{mcp.github_ref || 'main'}
                      </span>
                    )}
                    {mcp.root && (
                      <span className="text-xs text-gray-600 truncate max-w-[150px]">📁 {mcp.root}</span>
                    )}
                    {mcp.exclude && mcp.exclude.length > 0 && (
                      <span className="text-[10px] text-gray-600 border border-gray-700 rounded px-1.5 py-0.5">
                        exclude: {mcp.exclude.length} patterns
                      </span>
                    )}
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
