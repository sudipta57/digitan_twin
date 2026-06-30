import type { Figure, Topic } from '../types'

const FIGURES: Figure[] = [
  {
    id: 'feynman',
    name: 'Richard Feynman',
    years: '1918–1988',
    description: 'Theoretical physicist, Nobel laureate, eternal teacher.',
    portrait_url: '',
  },
  {
    id: 'tesla',
    name: 'Nikola Tesla',
    years: '1856–1943',
    description: 'Inventor of AC power, visionary engineer.',
    portrait_url: '',
  },
  {
    id: 'curie',
    name: 'Marie Curie',
    years: '1867–1934',
    description: 'Pioneer of radioactivity, first woman to win Nobel Prize.',
    portrait_url: '',
  },
]

const FIGURE_EMOJIS: Record<string, string> = {
  feynman: '⚛️',
  tesla: '⚡',
  curie: '☢️',
}

interface Props {
  selectedId: string | null
  onSelect: (id: string) => void
  topics: Topic[]
}

export function FigureSelector({ selectedId, onSelect, topics }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        Choose a Mind
      </h2>

      {FIGURES.map(fig => (
        <button
          key={fig.id}
          onClick={() => onSelect(fig.id)}
          className={`
            text-left p-4 rounded-xl border transition-all
            ${
              selectedId === fig.id
                ? 'border-amber-500 bg-amber-500/10 text-white'
                : 'border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:border-zinc-500'
            }
          `}
        >
          <div className="flex items-center gap-3 mb-1">
            <span className="text-2xl">{FIGURE_EMOJIS[fig.id]}</span>
            <div>
              <div className="font-semibold text-sm">{fig.name}</div>
              <div className="text-xs text-zinc-500">{fig.years}</div>
            </div>
          </div>
          <p className="text-xs text-zinc-400 mt-1">{fig.description}</p>
        </button>
      ))}

      {topics.length > 0 && (
        <div className="mt-2">
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
    </div>
  )
}
