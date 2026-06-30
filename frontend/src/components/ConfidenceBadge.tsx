import type { Confidence } from '../types'

const CONFIG: Record<Confidence, { label: string; color: string; dot: string }> = {
  direct: {
    label: 'Direct source',
    color: 'text-emerald-400 border-emerald-700 bg-emerald-900/30',
    dot: 'bg-emerald-400',
  },
  extrapolated: {
    label: 'Extrapolated',
    color: 'text-amber-400 border-amber-700 bg-amber-900/30',
    dot: 'bg-amber-400',
  },
  speculative: {
    label: 'Speculative',
    color: 'text-red-400 border-red-700 bg-red-900/30',
    dot: 'bg-red-400',
  },
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const c = CONFIG[confidence]
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${c.color}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}
