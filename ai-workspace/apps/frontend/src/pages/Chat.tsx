import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, StopCircle, Sparkles, Trash2, Wrench, CheckCircle2, XCircle } from 'lucide-react'
import { useChatStore, type ChatMessage } from '@/store/store'
import { cn, formatTimestamp } from '@/lib/utils'

export default function Chat() {
  const {
    messages,
    sessionId,
    streaming,
    provider,
    model,
    addMessage,
    setSessionId,
    setStreaming,
    setProvider,
    setModel,
    clearMessages,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [ws, setWs] = useState<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Create WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/chat/ws`
    const socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      console.log('WebSocket connected')
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'token') {
          // Update the last assistant message with accumulated content
          addMessage({
            role: 'assistant',
            content: data.content,
            timestamp: new Date().toISOString(),
          })
        } else if (data.type === 'tool_call') {
          // LLM requested a tool call
          const args = typeof data.args === 'string' ? data.args : JSON.stringify(data.args, null, 2)
          addMessage({
            role: 'tool',
            content: `🔧 **Tool Call:** \`${data.name}\`\n\`\`\`json\n${args}\n\`\`\``,
            timestamp: new Date().toISOString(),
          })
        } else if (data.type === 'tool_result') {
          // Tool execution result
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
          // Only add if there's actual content (don't add empty done for tool-only responses)
          if (data.content) {
            addMessage({
              role: 'assistant',
              content: data.content,
              timestamp: new Date().toISOString(),
            })
          }
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
      setStreaming(false)
    }

    socket.onclose = () => {
      console.log('WebSocket disconnected')
      setStreaming(false)
    }

    setWs(socket)

    return () => {
      socket.close()
    }
  }, [])

  const handleSend = () => {
    if (!input.trim() || streaming || !ws) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    }
    addMessage(userMessage)
    setInput('')
    setStreaming(true)

    ws.send(JSON.stringify({
      content: input.trim(),
      provider,
      model,
    }))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const providers = ['ollama', 'openrouter', 'gemini', 'openai']

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
              {streaming ? 'Streaming...' : `${provider} • ${model || 'No model selected'}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Provider Select */}
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="input-field text-xs py-1.5 w-32"
          >
            {providers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
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
              onClick={() => {
                ws?.close()
                setStreaming(false)
              }}
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
