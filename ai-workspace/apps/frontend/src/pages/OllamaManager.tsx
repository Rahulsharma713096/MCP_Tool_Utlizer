import { useEffect, useState } from 'react'
import { Play, Square, RotateCw, AlertTriangle, Download, Bot, Cpu, HardDrive, Activity } from 'lucide-react'
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
  const { installed, version, models, loading, setInstalled, setVersion, setModels, setLoading } = useOllamaStore()
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([])
  const [starting, setStarting] = useState<string | null>(null)

  useEffect(() => {
    checkOllama()
  }, [])

  const checkOllama = async () => {
    setLoading(true)
    try {
      const detection = await apiFetch<{ installed: boolean; version: string | null }>('/ollama/detect')
      setInstalled(detection.installed)
      setVersion(detection.version)

      if (detection.installed) {
        const modelsData = await apiFetch<{ models: OllamaModel[] }>('/ollama/models')
        setOllamaModels(modelsData.models)
      }
    } catch (err) {
      console.error('Ollama check failed:', err)
    } finally {
      setLoading(false)
    }
  }

  const startModel = async (modelName: string) => {
    setStarting(modelName)
    try {
      await apiFetch('/ollama/models/start', {
        method: 'POST',
        body: JSON.stringify({ name: modelName, provider: 'ollama' }),
      })
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
                        <span className="text-xs text-gray-600">{new Date(model.modified_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isRunning ? (
                      <button
                        onClick={() => stopModel(model.name)}
                        className="btn-danger flex items-center gap-2 text-sm"
                      >
                        <Square className="w-3 h-3" />
                        Stop
                      </button>
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
    </div>
  )
}
