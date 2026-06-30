import type { Contradiction } from '../types'

interface Props {
  contradictions: Contradiction[]
  loading: boolean
}

const RESOLUTION_LABELS = {
  unresolved: { label: 'Unresolved', color: 'text-red-400' },
  evolved: { label: 'Evolved over time', color: 'text-emerald-400' },
  context_dependent: { label: 'Context-dependent', color: 'text-amber-400' },
}

export function ContradictionLog({ contradictions, loading }: Props) {
  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3 px-1">
        Belief Contradictions
      </h2>

      {loading && (
        <p className="text-xs text-zinc-600 text-center py-4">Scanning memory graph...</p>
      )}

      {!loading && contradictions.length === 0 && (
        <p className="text-xs text-zinc-600 text-center py-4">
          No contradictions detected yet.
          <br />
          Select a figure to analyze their memory graph.
        </p>
      )}

      <div className="flex-1 overflow-y-auto space-y-3">
        {contradictions.map((c, i) => (
          <div
            key={i}
            className="rounded-xl border border-zinc-700 bg-zinc-800/50 overflow-hidden"
          >
            <div className="px-3 py-2 bg-zinc-800 flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-200 capitalize">{c.topic}</span>
              <span className={`text-[10px] ${RESOLUTION_LABELS[c.resolution].color}`}>
                {RESOLUTION_LABELS[c.resolution].label}
              </span>
            </div>

            <div className="px-3 pt-2">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-zinc-600">Tension</span>
                <div className="flex-1 h-1 bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-red-500"
                    style={{ width: `${c.tension_score * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-zinc-500">
                  {Math.round(c.tension_score * 100)}%
                </span>
              </div>
            </div>

            <div className="px-3 pb-3 space-y-2">
              <div className="rounded-lg bg-zinc-900/60 p-2">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-amber-400 font-medium">
                    {c.statement_a.source}
                  </span>
                  <span className="text-[10px] text-zinc-600">{c.statement_a.year}</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{c.statement_a.content}</p>
              </div>

              <div className="text-center text-zinc-600 text-[10px]">vs</div>

              <div className="rounded-lg bg-zinc-900/60 p-2">
                <div className="flex justify-between mb-1">
                  <span className="text-[10px] text-amber-400 font-medium">
                    {c.statement_b.source}
                  </span>
                  <span className="text-[10px] text-zinc-600">{c.statement_b.year}</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">{c.statement_b.content}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
