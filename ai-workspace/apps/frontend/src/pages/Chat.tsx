import { useState, useRef, useEffect, useMemo } from 'react'
import { Send, Bot, User, StopCircle, Sparkles, Trash2, Wrench, CheckCircle2, XCircle, ChevronDown, Cpu, Globe, Search, Loader2 } from 'lucide-react'
import { useChatStore, useOllamaStore, useProviderStore, type ChatMessage } from '@/store/store'
import { cn, formatTimestamp } from '@/lib/utils'

export default function Chat() {
  const {
    messages, sessionId, streaming, provider, model,
    addMessage, setSessionId, setStreaming, setProvider, setModel, clearMessages,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [ws, setWs] = useState<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const accumulatedTokens = useRef('')

  // Model selector state
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [modelSearch, setModelSearch] = useState('')
  const modelDropdownRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  // WebSocket connection with auto-reconnect
  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
    let socket: WebSocket | null = null

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/api/v1/chat/ws`
      socket = new WebSocket(wsUrl)

      socket.onopen = () => {
        console.log('WebSocket connected')
        setStreaming(false)
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'token') {
            accumulatedTokens.current += data.content
          } else if (data.type === 'tool_call') {
            const args = typeof data.args === 'string' ? data.args : JSON.stringify(data.args, null, 2)
            addMessage({
              role: 'tool',
              content: `🔧 **Tool Call:** \`${data.name}\`\n\`\`\`json\n${args}\n\`\`\``,
              timestamp: new Date().toISOString(),
            })
          } else if (data.type === 'tool_result') {
            const resultStr = typeof data.content === 'string' && data.content.length > 500
              ? data.content.substring(0, 500) + '...'
              : (typeof data.content === 'string' ? data.content : JSON.stringify(data.content))
            addMessage({
              role: 'tool',
              content: `✅ **Tool Result:** \`${data.name}\`\n\`\`\`\n${resultStr}\n\`\`\``,
              timestamp: new Date().toISOString(),
            })
          } else if (data.type === 'done') {
            setStreaming(false)
            if (accumulatedTokens.current.trim()) {
              addMessage({
                role: 'assistant',
                content: accumulatedTokens.current,
                timestamp: new Date().toISOString(),
              })
            }
            accumulatedTokens.current = ''
          } else if (data.type === 'error') {
            setStreaming(false)
            addMessage({
              role: 'assistant',
              content: `⚠️ Error: ${data.content}`,
              timestamp: new Date().toISOString(),
            })
          }
        } catch (err) {
          console.error('WebSocket message error:', err)
        }
      }

      socket.onerror = (err) => {
        console.error('WebSocket error:', err)
      }

      socket.onclose = () => {
        if (accumulatedTokens.current.trim()) {
          addMessage({
            role: 'assistant',
            content: accumulatedTokens.current,
            timestamp: new Date().toISOString(),
          })
          accumulatedTokens.current = ''
        }
        setStreaming(false)
        // Auto-reconnect after 3 seconds
        reconnectTimeout = setTimeout(connect, 3000)
      }

      setWs(socket)
    }

    connect()

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      socket?.close()
    }
  }, [])

  const handleSend = () => {
    if (!input.trim() || streaming || !ws) return
    const content = input.trim()
    setInput('')

    const userMessage: ChatMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }
    addMessage(userMessage)
    setStreaming(true)

    ws.send(JSON.stringify({ content, provider, model }))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Build unified model option list
  const ollamaModels = useOllamaStore((s) => s.models)
  const providerList = useProviderStore((s) => s.providers)

  interface ModelOption {
    label: string
    provider: string
    group: string
    providerType: 'local' | 'online'
    running?: boolean
  }

  const modelOptions = useMemo<{ group: string; options: ModelOption[] }[]>(() => {
    const groups: { group: string; options: ModelOption[] }[] = []

    // Local models from Ollama
    const localModels: ModelOption[] = ollamaModels.map((m) => ({
      label: m.name,
      provider: 'ollama',
      group: 'Local Models',
      providerType: 'local',
      running: m.running,
    }))
    if (localModels.length > 0) {
      groups.push({ group: 'Local Models', options: localModels })
    }

    // Online models from providers
    for (const prov of providerList) {
      if (prov.models && prov.models.length > 0 && prov.enabled) {
        const onlineModels: ModelOption[] = prov.models.map((m) => ({
          label: m,
          provider: prov.name.toLowerCase(),
          group: prov.name,
          providerType: 'online' as const,
        }))
        groups.push({ group: prov.name, options: onlineModels })
      }
    }

    return groups
  }, [ollamaModels, providerList])

  // Filter models by search
  const filteredModelOptions = useMemo(() => {
    if (!modelSearch.trim()) return modelOptions
    const q = modelSearch.toLowerCase()
    return modelOptions
      .map((group) => ({
        ...group,
        options: group.options.filter(
          (o) => o.label.toLowerCase().includes(q) || o.provider.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.options.length > 0)
  }, [modelOptions, modelSearch])

  const handleSelectModel = (opt: ModelOption) => {
    setProvider(opt.provider)
    setModel(opt.label)
    setShowModelDropdown(false)
    setModelSearch('')
  }

  const selectedOption = useMemo(() => {
    for (const group of modelOptions) {
      const found = group.options.find((o) => o.label === model && o.provider === provider)
      if (found) return found
    }
    return null
  }, [modelOptions, model, provider])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setShowModelDropdown(false)
        setModelSearch('')
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="flex flex-col h-full -m-6">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-gray-900/30">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10">
            <Bot className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-200">AI Chat</h3>
            <p className="text-xs text-gray-500">
              {streaming ? 'Streaming...' : (
                <>
                  {selectedOption ? (
                    <span className="flex items-center gap-1">
                      {selectedOption.providerType === 'local' ? (
                        <Cpu className="w-3 h-3 text-cyan-400" />
                      ) : (
                        <Globe className="w-3 h-3 text-purple-400" />
                      )}
                      <span className={selectedOption.providerType === 'local' ? 'text-cyan-400' : 'text-purple-400'}>
                        {selectedOption.provider}
                      </span>
                      <span className="text-gray-600">/</span>
                      <span className="text-gray-300">{selectedOption.label}</span>
                    </span>
                  ) : (
                    'No model selected — choose a model above'
                  )}
                </>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Unified Model Selector */}
          <div className="relative" ref={modelDropdownRef}>
            <button
              onClick={() => setShowModelDropdown(!showModelDropdown)}
              className="input-field text-xs py-1.5 pr-8 min-w-[200px] flex items-center gap-2 cursor-pointer"
            >
              {selectedOption ? (
                <>
                  {selectedOption.providerType === 'local' ? (
                    <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  ) : (
                    <Globe className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  )}
                  <span className="truncate">{selectedOption.label}</span>
                  <span className={cn(
                    'text-[10px] ml-auto px-1.5 py-0.5 rounded',
                    selectedOption.providerType === 'local' ? 'text-cyan-400 bg-cyan-500/10' : 'text-purple-400 bg-purple-500/10'
                  )}>
                    {selectedOption.provider}
                  </span>
                </>
              ) : (
                <span className="text-gray-500">Select model...</span>
              )}
              <ChevronDown className="w-3 h-3 text-gray-500 absolute right-2 top-1/2 -translate-y-1/2" />
            </button>

            {showModelDropdown && (
              <div className="absolute right-0 top-full mt-1 w-72 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 max-h-96 overflow-hidden flex flex-col">
                {/* Search bar */}
                <div className="p-2 border-b border-gray-800">
                  <div className="relative">
                    <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input
                      value={modelSearch}
                      onChange={(e) => setModelSearch(e.target.value)}
                      placeholder="Search models..."
                      className="w-full pl-7 pr-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-cyan-500/50"
                      autoFocus
                    />
                  </div>
                </div>

                {/* Model groups */}
                <div className="overflow-y-auto flex-1">
                  {filteredModelOptions.length === 0 ? (
                    <div className="p-4 text-center text-xs text-gray-500">
                      {modelSearch ? 'No models match your search' : 'No models available. Configure providers first.'}
                    </div>
                  ) : (
                    filteredModelOptions.map((group, gi) => [
                      <div key={`h-${gi}`} className="px-3 pt-2.5 pb-1.5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider sticky top-0 bg-gray-900/95 backdrop-blur-sm">
                        <div className="flex items-center gap-1.5">
                          {group.group === 'Local Models' ? (
                            <Cpu className="w-3 h-3 text-cyan-400" />
                          ) : (
                            <Globe className="w-3 h-3 text-purple-400" />
                          )}
                          {group.group}
                          <span className="text-[10px] text-gray-600 font-normal">({group.options.length})</span>
                        </div>
                      </div>,
                      ...group.options.map((opt) => {
                        const isSelected = opt.label === model && opt.provider === provider
                        return (
                          <button
                            key={`${opt.provider}-${opt.label}`}
                            onClick={() => handleSelectModel(opt)}
                            className={cn(
                              'w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs transition-colors',
                              isSelected ? 'bg-emerald-500/10 text-emerald-300' : 'text-gray-300 hover:bg-gray-800'
                            )}
                          >
                            <div className={cn(
                              'w-1.5 h-1.5 rounded-full shrink-0',
                              isSelected ? 'bg-emerald-500' : opt.providerType === 'local' ? 'bg-cyan-500' : 'bg-purple-500'
                            )} />
                            <span className="truncate flex-1">{opt.label}</span>
                            {opt.running && (
                              <span className="text-[10px] text-emerald-400 flex items-center gap-1 shrink-0">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                running
                              </span>
                            )}
                          </button>
                        )
                      }),
                    ])
                  )}
                </div>
              </div>
            )}
          </div>
          {/* Clear Chat */}
          <button
            onClick={clearMessages}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-red-400 transition-all"
            title="Clear chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="p-4 rounded-full bg-emerald-500/10 mb-4">
              <Sparkles className="w-8 h-8 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-300">Start a Conversation</h3>
            <p className="text-sm text-gray-500 mt-2 max-w-md">
              Send a message to begin interacting with your AI models.
              Choose a provider and model from the top bar.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={cn(
              'flex gap-3 animate-slide-up',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-cyan-400" />
              </div>
            )}

            {msg.role === 'tool' && (
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
                <Wrench className="w-4 h-4 text-amber-400" />
              </div>
            )}

            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-emerald-400" />
              </div>
            )}

            <div
              className={cn(
                'max-w-[70%] rounded-2xl px-4 py-3',
                msg.role === 'user'
                  ? 'bg-emerald-600/20 border border-emerald-500/20 text-gray-200'
                  : msg.role === 'tool'
                  ? 'bg-amber-500/5 border border-amber-500/15 text-gray-300 font-mono text-xs'
                  : 'bg-gray-800/50 border border-gray-700/30 text-gray-300'
              )}
            >
              {msg.role === 'tool' ? (
                <div className="whitespace-pre-wrap">
                  {msg.content.split('```').map((part, i) =>
                    i % 2 === 0 ? (
                      <span key={i}>{part}</span>
                    ) : (
                      <code key={i} className="block bg-gray-900/50 rounded p-2 my-1 overflow-x-auto text-[11px]">{part}</code>
                    )
                  )}
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              )}
              <p className="text-xs text-gray-600 mt-2">{formatTimestamp(msg.timestamp)}</p>
            </div>
          </div>
        ))}

        {streaming && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            </div>
            <div className="bg-gray-800/50 border border-gray-700/30 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-gray-800 bg-gray-900/30">
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Shift+Enter for new line)"
            rows={1}
            className="input-field resize-none min-h-[44px] max-h-[120px] py-3"
          />
          {streaming ? (
            <button
              onClick={() => { ws?.close(); setStreaming(false) }}
              className="btn-danger h-[44px] px-4 flex items-center gap-2"
            >
              <StopCircle className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              aria-label="Send message"
              className="btn-primary h-[44px] px-4 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
