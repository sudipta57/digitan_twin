import { useState, useEffect, useCallback } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Sidebar } from './components/Sidebar'
import { ChatWindow } from './components/ChatWindow'
import { ContradictionLog } from './components/ContradictionLog'
import { useChat } from './hooks/useChat'
import { useFigure } from './hooks/useFigure'
import { apiClient } from './api/client'
import type { FigureInfo } from './types'

function AppInner() {
  const { user } = useAuth()
  const [selected, setSelected] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [publicFigures, setPublicFigures] = useState<FigureInfo[]>([])
  const [personalFigures, setPersonalFigures] = useState<FigureInfo[]>([])

  const { topics, contradictions, loading: figureLoading } = useFigure(selected)
  const { messages, loading: chatLoading, error, sendMessage, clearMessages } = useChat(selected)

  const refreshFigures = useCallback(() => {
    apiClient.getFigures()
      .then(res => { setPublicFigures(res.public); setPersonalFigures(res.personal) })
      .catch(console.error)
  }, [])

  useEffect(() => { refreshFigures() }, [refreshFigures, user])

  const handleSelect = (id: string) => {
    const fig = [...publicFigures, ...personalFigures].find(f => f.id === id)
    setSelected(id)
    setSelectedName(fig?.name ?? null)
    clearMessages()
  }

  const handleTwinCreated = (figureId: string, name: string) => {
    refreshFigures()
    setSelected(figureId)
    setSelectedName(name)
    clearMessages()
  }

  const handleFigureDeleted = (figureId: string) => {
    refreshFigures()
    if (selected === figureId) {
      setSelected(null)
      setSelectedName(null)
      clearMessages()
    }
  }

  return (
    <div className="h-screen bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">👻</span>
          <div>
            <h1 className="text-sm font-bold text-white">Dead People's Digital Twin</h1>
            <p className="text-[10px] text-zinc-500">
              Historical figures + personal memories, grounded in source
            </p>
          </div>
        </div>
        {selectedName && (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Talking to {selectedName}
          </div>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-72 shrink-0 border-r border-zinc-800 p-4 overflow-y-auto">
          <Sidebar
            publicFigures={publicFigures}
            personalFigures={personalFigures}
            selectedId={selected}
            topics={topics}
            onSelect={handleSelect}
            onTwinCreated={handleTwinCreated}
            onFigureDeleted={handleFigureDeleted}
          />
        </aside>

        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            loading={chatLoading}
            error={error}
            onSend={sendMessage}
            figureName={selectedName}
          />
        </main>

        <aside className="w-72 shrink-0 border-l border-zinc-800 p-4 overflow-y-auto">
          <ContradictionLog contradictions={contradictions} loading={figureLoading} />
        </aside>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  )
}
