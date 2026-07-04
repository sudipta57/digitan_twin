import { useState } from 'react'
import type { FigureInfo, Topic } from '../types'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../api/client'
import { LoginButton } from './LoginButton'
import { CreateTwinModal } from './CreateTwinModal'

const PUBLIC_FIGURE_EMOJIS: Record<string, string> = {
  feynman: '⚛️',
  tesla: '⚡',
  curie: '☢️',
}

interface Props {
  publicFigures: FigureInfo[]
  personalFigures: FigureInfo[]
  selectedId: string | null
  topics: Topic[]
  onSelect: (id: string) => void
  onTwinCreated: (figureId: string, name: string) => void
  onFigureDeleted: (figureId: string) => void
}

export function Sidebar({ publicFigures, personalFigures, selectedId, topics, onSelect, onTwinCreated, onFigureDeleted }: Props) {
  const { user, loading, logout } = useAuth()
  const [modalOpen, setModalOpen] = useState(false)

  const handleDelete = async (e: React.MouseEvent, figureId: string) => {
    e.stopPropagation()
    if (!confirm('Permanently delete this twin and its entire memory graph?')) return
    try {
      await apiClient.deleteFigure(figureId)
      onFigureDeleted(figureId)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">
          Historical Figures
        </h2>
        <div className="flex flex-col gap-3">
          {publicFigures.map(fig => (
            <button
              key={fig.id}
              onClick={() => onSelect(fig.id)}
              className={`text-left p-4 rounded-xl border transition-all ${
                selectedId === fig.id
                  ? 'border-amber-500 bg-amber-500/10 text-white'
                  : 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500'
              }`}
            >
              <div className="flex items-center gap-3 mb-1">
                <span className="text-2xl">{PUBLIC_FIGURE_EMOJIS[fig.id] ?? '🧠'}</span>
                <div>
                  <div className="font-semibold text-sm">{fig.name}</div>
                  <div className="text-xs text-zinc-500">{fig.years}</div>
                </div>
              </div>
              <p className="text-xs text-zinc-400 mt-1">{fig.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
            My Twins
          </h2>
          {user && (
            <button onClick={() => setModalOpen(true)}
              className="text-xs text-amber-400 hover:text-amber-300 font-medium">
              + Create
            </button>
          )}
        </div>

        {!loading && !user && (
          <div className="p-4 rounded-xl border border-dashed border-zinc-700 text-center flex flex-col items-center gap-2">
            <p className="text-xs text-zinc-500">Sign in to build a private twin of someone you knew.</p>
            <LoginButton />
          </div>
        )}

        {user && personalFigures.length === 0 && (
          <button onClick={() => setModalOpen(true)}
            className="w-full p-4 rounded-xl border border-dashed border-zinc-700 text-xs text-zinc-500 hover:border-amber-500 hover:text-amber-400 transition-colors">
            + Create your first twin
          </button>
        )}

        {user && personalFigures.length > 0 && (
          <div className="flex flex-col gap-3">
            {personalFigures.map(fig => (
              <button
                key={fig.id}
                onClick={() => onSelect(fig.id)}
                className={`group text-left p-4 rounded-xl border transition-all ${
                  selectedId === fig.id
                    ? 'border-amber-500 bg-amber-500/10 text-white'
                    : 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{fig.name}</div>
                    <div className="text-xs text-zinc-500">
                      {fig.years}{fig.relationship ? ` · ${fig.relationship}` : ''}
                    </div>
                  </div>
                  <span
                    onClick={e => handleDelete(e, fig.id)}
                    className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 text-xs transition-opacity"
                  >
                    delete
                  </span>
                </div>
                {fig.description && <p className="text-xs text-zinc-400 mt-1">{fig.description}</p>}
                <p className="text-[10px] text-zinc-600 mt-1">{fig.source_count ?? 0} sources ingested</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {user && (
        <div className="flex items-center justify-between px-1 pt-2 border-t border-zinc-800">
          <span className="text-xs text-zinc-500 truncate">{user.name}</span>
          <button onClick={logout} className="text-xs text-zinc-600 hover:text-zinc-300">
            Sign out
          </button>
        </div>
      )}

      {topics.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-2">
            Knowledge Clusters
          </h3>
          <div className="flex flex-wrap gap-2">
            {topics.map(topic => (
              <span
                key={topic.name}
                className="px-2 py-1 rounded-full text-xs bg-zinc-800 border border-zinc-700 text-zinc-300"
                style={{ opacity: 0.5 + topic.strength * 0.5 }}
              >
                {topic.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {modalOpen && (
        <CreateTwinModal
          onClose={() => setModalOpen(false)}
          onCreated={(figureId, name) => {
            setModalOpen(false)
            onTwinCreated(figureId, name)
          }}
        />
      )}
    </div>
  )
}
