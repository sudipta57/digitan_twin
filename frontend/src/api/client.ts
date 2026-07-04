import axios from 'axios'
import type { Message, Citation, Contradiction, Topic, FigureInfo, UserInfo, CreateFigurePayload, DocType } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL, timeout: 60000, withCredentials: true })

// Ingestion runs cognee.cognify() on the whole dataset synchronously, which can take well
// past a minute for anything beyond a trivial snippet — give it a much longer budget than
// interactive calls so a slow-but-healthy ingest doesn't get killed client-side and reported
// as "Failed" while the backend is still working.
const INGEST_TIMEOUT_MS = 180000

export interface ChatResponse {
  response: string
  citations: Citation[]
  sources_used: number
  confidence: 'direct' | 'extrapolated' | 'speculative'
  contradiction_flag: boolean
}

export interface FiguresResponse {
  public: FigureInfo[]
  personal: FigureInfo[]
}

export interface IngestResponse {
  status: string
  nodes_created: number
  topics_detected: string[]
  processing_time_ms: number
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`))
    reader.readAsDataURL(file)
  })
}

export const apiClient = {
  async loginWithGoogle(token: string): Promise<UserInfo> {
    const res = await api.post('/auth/google', { token })
    return res.data
  },

  async getMe(): Promise<UserInfo> {
    const res = await api.get('/auth/me')
    return res.data
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },

  async getFigures(): Promise<FiguresResponse> {
    const res = await api.get('/figures')
    return res.data
  },

  async createFigure(payload: CreateFigurePayload): Promise<{ figure_id: string; slug: string; dataset_name: string }> {
    const res = await api.post('/figures', payload)
    return res.data
  },

  async deleteFigure(figureId: string): Promise<void> {
    await api.delete(`/figures/${figureId}`)
  },

  async ingestText(figureId: string, text: string, title: string, year: number, docType: DocType): Promise<IngestResponse> {
    const res = await api.post('/ingest', {
      figure_id: figureId,
      source_type: 'text',
      content: text,
      metadata: { title, year, doc_type: docType },
    }, { timeout: INGEST_TIMEOUT_MS })
    return res.data
  },

  async ingestUrl(figureId: string, url: string, title: string, year: number, docType: DocType = 'article'): Promise<IngestResponse> {
    const res = await api.post('/ingest', {
      figure_id: figureId,
      source_type: 'url',
      content: url,
      metadata: { title, year, doc_type: docType },
    }, { timeout: INGEST_TIMEOUT_MS })
    return res.data
  },

  async ingestPdf(figureId: string, file: File, title: string, year: number): Promise<IngestResponse> {
    const content = await toBase64(file)
    const res = await api.post('/ingest', {
      figure_id: figureId,
      source_type: 'pdf',
      content,
      metadata: { title, year, doc_type: 'book' },
    }, { timeout: INGEST_TIMEOUT_MS })
    return res.data
  },

  async ingestWhatsapp(figureId: string, file: File, senderName: string, year: number): Promise<IngestResponse> {
    const content = await file.text()
    const res = await api.post('/ingest', {
      figure_id: figureId,
      source_type: 'whatsapp',
      content,
      metadata: { title: file.name, year, doc_type: 'whatsapp' },
      whatsapp_sender_name: senderName,
    }, { timeout: INGEST_TIMEOUT_MS })
    return res.data
  },

  async chat(figureId: string, message: string, history: Message[]): Promise<ChatResponse> {
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
