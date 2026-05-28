import { useEffect, useState } from 'react'
import { Play, Square, RotateCw, AlertTriangle, Download, Bot, Cpu, HardDrive, Activity, MessageSquare, Send, X } from 'lucide-react'
import { toast } from 'sonner'
import { apiFetch, cn, formatBytes, getStatusColor, getStatusDot } from '@/lib/utils'
import { useOllamaStore } from '@/store/store'

interface OllamaModel {
  name: string
  size: number
  quantization: string
  modified_at: string
}

export default function OllamaManager() {
  const { installed, version, models, loading, setInstalled, setVersion, setModels, setLoading, toggleModel, startModelOnly } = useOllamaStore()
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([])
  const [starting, setStarting] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [testChatModel, setTestChatModel] = useState<string | null>(null)
  const [testInput, setTestInput] = useState('')
  const [testResponse, setTestResponse] = useState('')
  const [testLoading, setTestLoading] = useState(false)

  const handleTestChat = async () => {
    if (!testChatModel || !testInput.trim()) return
    setTestLoading(true)
    setTestResponse('')
    try {
      const result = await apiFetch<{ response: string }>('/chat/send', {
        method: 'POST',
        body: JSON.stringify({
          session_id: `test-ollama-${testChatModel}-${Date.now()}`,
          content: testInput.trim(),
          provider: 'ollama',
          model: testChatModel,
        }),
      })
      setTestResponse(result.response || 'No response')
    } catch (err: any) {
      setTestResponse(`Error: ${err.message}`)
    } finally {
      setTestLoading(false)
    }
  }

  useEffect(() => {
    checkOllama()
  }, [])

  const checkOllama = async () => {
    setLoading(true)
    setApiError(null)
    try {
      const detection = await apiFetch<{ installed: boolean; version: string | null }>('/ollama/detect')
      setInstalled(detection.installed)
      setVersion(detection.version)

      if (detection.installed) {
        const modelsData = await apiFetch<{ models: OllamaModel[]; count?: number }>('/ollama/models')
        setOllamaModels(modelsData.models)
        // Check which model is currently running via Ollama API
        let runningModel = ''
        try {
          const psResult = await apiFetch<{ models?: Array<{ name: string }> }>('/ollama/models')
          // If we can detect running models, mark them
          // For now, initialize all as not running — user will start explicitly
        } catch {
          // Ignore — Ollama ps endpoint may not be available
        }
        setModels(modelsData.models.map((m) => ({
          name: m.name,
          running: m.name === runningModel,
          cpu_usage: 0,
          ram_usage: 0,
          size: m.size.toString(),
          quantization: m.quantization,
        })))
        if (modelsData.models.length === 0) {
          setApiError('Ollama is installed but no models found. Run "ollama pull <model>" in your terminal to download models.')
        }
      }
    } catch (err: any) {
      console.error('Ollama check failed:', err)
      setApiError(`Failed to connect to backend: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const startModel = async (modelName: string) => {
    setStarting(modelName)
    try {
      // Find any currently running model and stop it first (single-model selection)
      const runningModel = models.find((m) => m.running)
      if (runningModel && runningModel.name !== modelName) {
        try {
          await apiFetch('/ollama/models/stop', {
            method: 'POST',
            body: JSON.stringify({ name: runningModel.name }),
          })
        } catch {
          // If stop fails, still try to start the new model
        }
      }

      // Start the requested model
      await apiFetch('/ollama/models/start', {
        method: 'POST',
        body: JSON.stringify({ name: modelName, provider: 'ollama' }),
      })
      // Mark only this model as running, all others as not
      startModelOnly(modelName)
      toast.success(`Started ${modelName}`)
    } catch (err: any) {
      toast.error(`Failed to start ${modelName}: ${err.message}`)
    } finally {
      setStarting(null)
    }
  }

  const stopModel = async (modelName: string) => {
    try {
      await apiFetch('/ollama/models/stop', {
        method: 'POST',
        body: JSON.stringify({ name: modelName }),
      })
      // Mark model as not running in the store
      toggleModel(modelName)
      toast.success(`Stopped ${modelName}`)
    } catch (err: any) {
      toast.error(`Failed to stop ${modelName}: ${err.message}`)
    }
  }

  if (!installed && !loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="p-6 rounded-full bg-yellow-500/10 mb-6">
          <AlertTriangle className="w-12 h-12 text-yellow-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-200">Ollama Not Detected</h2>
        <p className="text-gray-500 mt-2 max-w-md">
          Ollama is required to run local AI models. Please install it to get started.
        </p>
        <div className="flex gap-3 mt-6">
          <a
            href="https://ollama.com/download"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download Ollama
          </a>
          <button onClick={checkOllama} className="btn-secondary flex items-center gap-2">
            <RotateCw className="w-4 h-4" />
            Check Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Ollama Runtime Manager</h1>
          <p className="page-description">Manage local LLMs via Ollama</p>
        </div>
        <div className="flex items-center gap-3">
          {version && (
            <span className="badge badge-active">{version}</span>
          )}
          <button onClick={checkOllama} className="btn-secondary flex items-center gap-2">
            <RotateCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* API Error Banner */}
      {apiError && (
        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
          <div className="text-sm text-yellow-300/90">{apiError}</div>
          <button onClick={checkOllama} className="ml-auto btn-secondary text-xs flex items-center gap-1 px-3 py-1.5">
            <RotateCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Models', value: ollamaModels.length, icon: Bot, color: 'text-emerald-400' },
          { label: 'Running', value: models.filter((m) => m.running).length, icon: Activity, color: 'text-cyan-400' },
          { label: 'Total Size', value: formatBytes(ollamaModels.reduce((a, m) => a + (m.size || 0), 0)), icon: HardDrive, color: 'text-purple-400' },
        ].map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="glass-card">
              <div className="flex items-center gap-3 mb-2">
                <Icon className={cn('w-5 h-5', stat.color)} />
                <span className="text-xs text-gray-500">{stat.label}</span>
              </div>
              <div className="text-2xl font-bold text-gray-100">{stat.value}</div>
            </div>
          )
        })}
      </div>

      {/* Models List */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-300">Installed Models</h3>
        </div>
        <div className="divide-y divide-gray-800/50">
          {ollamaModels.length === 0 ? (
            <div className="px-4 py-12 text-center text-gray-500">
              <Bot className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p>No models installed. Run <code className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">ollama pull llama3</code> to get started.</p>
            </div>
          ) : (
            ollamaModels.map((model) => {
              const isRunning = models.find((m) => m.name === model.name)?.running || false
              const isStarting = starting === model.name
              return (
                <div key={model.name} className="flex items-center justify-between px-4 py-3 hover:bg-gray-800/30 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className={cn('w-2 h-2 rounded-full', isRunning ? 'bg-emerald-500 animate-pulse' : 'bg-gray-600')} />
                    <div>
                      <div className="text-sm font-medium text-gray-200">{model.name}</div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-500">{formatBytes(model.size)}</span>
                        <span className="text-xs text-gray-600">{model.quantization}</span>
                        <span className="text-xs text-gray-600">{model.modified_at ? new Date(model.modified_at).toLocaleDateString() : '—'}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isRunning ? (
                      <>
                        <button
                          onClick={() => { setTestChatModel(model.name); setTestInput('Hello, what can you do?'); setTestResponse('') }}
                          className="btn-secondary flex items-center gap-2 text-sm"
                        >
                          <MessageSquare className="w-3 h-3" />
                          Test Chat
                        </button>
                        <button
                          onClick={() => stopModel(model.name)}
                          className="btn-danger flex items-center gap-2 text-sm"
                        >
                          <Square className="w-3 h-3" />
                          Stop
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => startModel(model.name)}
                        disabled={isStarting}
                        className="btn-primary flex items-center gap-2 text-sm"
                      >
                        <Play className={cn('w-3 h-3', isStarting && 'animate-pulse')} />
                        {isStarting ? 'Starting...' : 'Start'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
      {/* Test Chat Dialog */}
      {testChatModel && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setTestChatModel(null)}>
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-lg w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-200">Test Chat — {testChatModel}</h3>
              <button onClick={() => setTestChatModel(null)} className="p-1 hover:bg-gray-800 rounded-lg">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            <div className="mb-3">
              <input
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTestChat() } }}
                placeholder="Type a test message..."
                className="input-field"
              />
            </div>
            <button
              onClick={handleTestChat}
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
    </div>
  )
}
