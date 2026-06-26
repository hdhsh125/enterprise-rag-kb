export interface UserInfo {
  user_id: string
  username: string
  role: 'admin' | 'user'
  created_at: number
}

/** Four RAG modes exposed in the UI */
export type RagMode = 'basic' | 'auto' | 'vectorstore' | 'web_search'

export interface ChatSession {
  session_id: string
  title: string
  created_at: number
  last_active: number
}

export interface DisplayMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  isError?: boolean
}

export interface SourceDocument {
  title: string
  category: string
  preview: string
}

export interface WorkflowNode {
  name: string
  label: string
  status: 'idle' | 'active' | 'done'
}

export interface DocRecord {
  doc_id: string
  filename: string
  chunk_count: number
  uploaded_at: number
}

export type SSEEventType = 'node_start' | 'node_complete' | 'token' | 'sources' | 'done' | 'error'

export interface SSEEvent {
  type: SSEEventType
  data: Record<string, unknown>
}
