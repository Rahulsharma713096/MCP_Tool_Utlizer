import { useState } from 'react'
import { Toaster } from 'sonner'
import Sidebar from './components/Sidebar'
import TopNav from './components/TopNav'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import OllamaManager from './pages/OllamaManager'
import MCPStudio from './pages/MCPStudio'
import Providers from './pages/Providers'
import RuntimeMonitor from './pages/RuntimeMonitor'
import Logs from './pages/Logs'
import Settings from './pages/Settings'

const pages: Record<string, React.ReactNode> = {
  dashboard: <Dashboard />,
  chat: <Chat />,
  ollama: <OllamaManager />,
  mcp: <MCPStudio />,
  providers: <Providers />,
  runtime: <RuntimeMonitor />,
  logs: <Logs />,
  settings: <Settings />,
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      <Sidebar activePage={activePage} onPageChange={setActivePage} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav activePage={activePage} />
        <main className="flex-1 overflow-y-auto p-6">
          {pages[activePage] || <Dashboard />}
        </main>
      </div>
    </div>
  )
}
