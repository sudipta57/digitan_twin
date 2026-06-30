export type DocType = 'book' | 'interview' | 'lecture' | 'letter' | 'article' | 'paper' | 'testimony'
export type Confidence = 'direct' | 'extrapolated' | 'speculative'

export interface Citation {
  quote: string
  source: string
  year: number
  doc_type: DocType
  relevance_score: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  confidence?: Confidence
  contradiction_flag?: boolean
  sources_used?: number
  timestamp: Date
}

export interface Contradiction {
  topic: string
  statement_a: { content: string; source: string; year: number }
  statement_b: { content: string; source: string; year: number }
  tension_score: number
  resolution: 'unresolved' | 'evolved' | 'context_dependent'
}

export interface Topic {
  name: string
  strength: number
  source_count: number
}

export interface Figure {
  id: string
  name: string
  years: string
  description: string
  portrait_url: string
}
