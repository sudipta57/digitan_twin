import { useState, useCallback } from 'react'
import { apiClient } from '../api/client'
import type { Message } from '../types'

export function useChat(figureId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(
    async (text: string) => {
      if (!figureId || !text.trim()) return

      const userMessage: Message = {
        role: 'user',
        content: text,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, userMessage])
      setLoading(true)
      setError(null)

      try {
        const response = await apiClient.chat(figureId, text, messages)

        const assistantMessage: Message = {
          role: 'assistant',
          content: response.response,
          citations: response.citations,
          confidence: response.confidence,
          contradiction_flag: response.contradiction_flag,
          sources_used: response.sources_used,
          timestamp: new Date(),
        }

        setMessages(prev => [...prev, assistantMessage])
      } catch {
        setError('Failed to get a response. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [figureId, messages],
  )

  const clearMessages = useCallback(() => setMessages([]), [])

  return { messages, loading, error, sendMessage, clearMessages }
}
