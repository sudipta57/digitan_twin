import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'
import type { Topic, Contradiction } from '../types'

export function useFigure(figureId: string | null) {
  const [topics, setTopics] = useState<Topic[]>([])
  const [contradictions, setContradictions] = useState<Contradiction[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!figureId) return

    setLoading(true)
    Promise.all([
      apiClient.getTopics(figureId),
      apiClient.getContradictions(figureId),
    ])
      .then(([t, c]) => {
        setTopics(t)
        setContradictions(c)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [figureId])

  return { topics, contradictions, loading }
}
