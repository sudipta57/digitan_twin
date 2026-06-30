import { useState } from 'react'
import { FigureSelector } from './components/FigureSelector'
import { ChatWindow } from './components/ChatWindow'
import { ContradictionLog } from './components/ContradictionLog'
import { useChat } from './hooks/useChat'
import { useFigure } from './hooks/useFigure'

const FIGURE_NAMES: Record<string, string> = {
  feynman: 'Richard Feynman',
  tesla: 'Nikola Tesla',
  curie: 'Marie Curie',
}

export default function App() {
  const [selectedFigure, setSelectedFigure] = useState<string | null>(null)
  const { topics, contradictions, loading: figureLoading } = useFigure(selectedFigure)
  const { messages, loading: chatLoading, error, sendMessage, clearMessages } = useChat(selectedFigure)

  const handleSelectFigure = (id: string) => {
    setSelectedFigure(id)
    clearMessages()
  }

  return (
    <div className="h-screen bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">👻</span>
          <div>
            <h1 className="text-sm font-bold text-white">Dead People's Digital Twin</h1>
            <p className="text-[10px] text-zinc-500">
              Source-grounded conversations with history's greatest minds
            </p>
          </div>
        </div>
        {selectedFigure && (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Talking to {FIGURE_NAMES[selectedFigure]}
          </div>
        )}
      </header>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left — Figure selector */}
        <aside className="w-64 shrink-0 border-r border-zinc-800 p-4 overflow-y-auto">
          <FigureSelector
            selectedId={selectedFigure}
            onSelect={handleSelectFigure}
            topics={topics}
          />
        </aside>

        {/* Center — Chat */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            loading={chatLoading}
            error={error}
            onSend={sendMessage}
            figureName={selectedFigure ? FIGURE_NAMES[selectedFigure] : null}
          />
        </main>

        {/* Right — Contradiction log */}
        <aside className="w-72 shrink-0 border-l border-zinc-800 p-4 overflow-y-auto">
          <ContradictionLog contradictions={contradictions} loading={figureLoading} />
        </aside>
      </div>
    </div>
  )
}
