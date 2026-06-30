import axios from 'axios'
import type { Citation, Contradiction, Topic, Figure, Message } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL, timeout: 30000 })

export interface ChatResponse {
  response: string
  citations: Citation[]
  sources_used: number
  confidence: 'direct' | 'extrapolated' | 'speculative'
  contradiction_flag: boolean
}

export const apiClient = {
  async getFigures(): Promise<Figure[]> {
    const res = await api.get('/figures')
    return res.data.figures
  },

  async chat(
    figureId: string,
    message: string,
    history: Message[],
  ): Promise<ChatResponse> {
    const res = await api.post('/chat', {
      figure_id: figureId,
      message,
      conversation_history: history.map(m => ({ role: m.role, content: m.content })),
    })
    return res.data
  },

  async getContradictions(figureId: string): Promise<Contradiction[]> {
    const res = await api.get(`/contradictions/${figureId}`)
    return res.data.contradictions
  },

  async getTopics(figureId: string): Promise<Topic[]> {
    const res = await api.get(`/topics/${figureId}`)
    return res.data.topics
  },
}
