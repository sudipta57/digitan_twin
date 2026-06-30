import { useRef, useEffect, useState } from 'react'
import type { Message } from '../types'
import { CitationCard } from './CitationCard'
import { ConfidenceBadge } from './ConfidenceBadge'

interface Props {
  messages: Message[]
  loading: boolean
  error: string | null
  onSend: (text: string) => void
  figureName: string | null
}

const STARTER_PROMPTS = [
  'What was your greatest mistake?',
  'Did you ever doubt yourself?',
  'What do you think about modern technology?',
  'What should young people focus on?',
]

export function ChatWindow({ messages, loading, error, onSend, figureName }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = () => {
    if (!input.trim() || loading) return
    onSend(input.trim())
    setInput('')
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && figureName && (
          <div className="text-center py-8">
            <p className="text-zinc-500 text-sm mb-4">
              Start a conversation with {figureName}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {STARTER_PROMPTS.map(p => (
                <button
                  key={p}
                  onClick={() => onSend(p)}
                  className="px-3 py-2 text-xs rounded-lg border border-zinc-700 text-zinc-400 hover:border-amber-600 hover:text-amber-400 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.length === 0 && !figureName && (
          <div className="text-center py-16">
            <p className="text-zinc-600 text-sm">Select a historical figure to begin</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              {msg.role === 'assistant' && msg.confidence && (
                <ConfidenceBadge confidence={msg.confidence} />
              )}

              <div
                className={`
                  px-4 py-3 rounded-2xl text-sm leading-relaxed
                  ${
                    msg.role === 'user'
                      ? 'bg-amber-600 text-white rounded-br-sm'
                      : 'bg-zinc-800 text-zinc-100 rounded-bl-sm border border-zinc-700'
                  }
                `}
              >
                {msg.content}
              </div>

              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <CitationCard citations={msg.citations} />
              )}

              {msg.role === 'assistant' && msg.contradiction_flag && (
                <span className="text-[10px] text-amber-500 flex items-center gap-1">
                  ⚡ Contains belief contradiction
                </span>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800 border border-zinc-700 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 bg-amber-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {error && <div className="text-center text-xs text-red-400 py-2">{error}</div>}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-zinc-700/50 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={figureName ? `Ask ${figureName} anything...` : 'Select a figure first'}
            disabled={!figureName || loading}
            rows={2}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 resize-none focus:outline-none focus:border-amber-500 disabled:opacity-40"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || loading || !figureName}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors self-end"
          >
            Send
          </button>
        </div>
        <p className="text-[10px] text-zinc-600 mt-2 text-center">
          All responses grounded in documented source material via Cognee memory graph
        </p>
      </div>
    </div>
  )
}
