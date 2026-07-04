import { useState } from 'react'
import type { Citation } from '../types'

const DOC_TYPE_ICONS: Record<string, string> = {
  book: '📖',
  lecture: '🎓',
  interview: '🎙️',
  testimony: '⚖️',
  article: '📰',
  letter: '✉️',
  paper: '📄',
  whatsapp: '💬',
  diary: '📔',
}

interface Props {
  citations: Citation[]
}

export function CitationCard({ citations }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!citations.length) return null

  return (
    <div className="mt-2 border border-zinc-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-800/80 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <span>
          {DOC_TYPE_ICONS[citations[0]?.doc_type] ?? '📎'} {citations.length} source
          {citations.length > 1 ? 's' : ''}
        </span>
        <span>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="divide-y divide-zinc-700/50">
          {citations.map((c, i) => (
            <div key={i} className="px-3 py-2 bg-zinc-900/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-amber-400">{c.source}</span>
                <span className="text-xs text-zinc-500">{c.year}</span>
              </div>
              <p className="text-xs text-zinc-400 italic">"{c.quote}"</p>
              <div className="mt-1 flex items-center gap-1">
                <div
                  className="h-1 rounded-full bg-amber-500"
                  style={{ width: `${c.relevance_score * 100}%`, maxWidth: '80px' }}
                />
                <span className="text-[10px] text-zinc-600">
                  {Math.round(c.relevance_score * 100)}% match
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
