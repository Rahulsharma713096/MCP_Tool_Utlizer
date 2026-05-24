import { Bell, Search, Maximize2, Minimize2 } from 'lucide-react'
import { useState } from 'react'
import { formatTimestamp } from '@/lib/utils'

interface TopNavProps {
  activePage: string
}

const pageTitles: Record<string, string> = {
  dashboard: 'Dashboard',
  chat: 'AI Chat',
  ollama: 'Ollama Runtime Manager',
  mcp: 'MCP Studio',
  providers: 'Provider Manager',
  runtime: 'Runtime Monitor',
  logs: 'System Logs',
  settings: 'Settings',
}

export default function TopNav({ activePage }: TopNavProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [time, setTime] = useState(new Date().toLocaleTimeString())

  // Update time every second
  useState(() => {
    const interval = setInterval(() => {
      setTime(new Date().toLocaleTimeString())
    }, 1000)
    return () => clearInterval(interval)
  })

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  return (
    <header className="h-16 bg-gray-900/40 backdrop-blur-xl border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-100">
          {pageTitles[activePage] || 'Dashboard'}
        </h2>
        <span className="text-xs text-gray-600 hidden sm:inline">
          {time}
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 pl-9 pr-3 py-1.5 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
          />
        </div>

        {/* Fullscreen */}
        <button
          onClick={toggleFullscreen}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-all"
          title="Toggle fullscreen"
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>

        {/* Notifications */}
        <button className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-all relative">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        </button>

        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-xs font-bold text-white">
          A
        </div>
      </div>
    </header>
  )
}
