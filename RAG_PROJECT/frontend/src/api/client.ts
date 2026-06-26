/**
 * API client — thin wrapper over fetch with:
 *   - Automatic Bearer token injection from Zustand auth store
 *   - Unified 401 → logout handling
 *   - SSE streaming via AsyncGenerator
 */
import type { SourceDocument, SSEEvent } from '../types'

const BASE = 'http://localhost:8000/api/v1'

function getToken(): string | null {
  // Lazy import avoids circular dependency with authStore
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const stored = JSON.parse(localStorage.getItem('rag-auth') || '{}') as any
    return stored?.state?.token ?? null
  } catch {
    return null
  }
}

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

function handle401() {
  localStorage.removeItem('rag-auth')
  window.location.href = '/login'
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    const detail = body.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join('; ')
    return JSON.stringify(detail)
  } catch {
    return res.statusText
  }
}

async function ok<T>(res: Response): Promise<T> {
  if (res.status === 401) { handle401(); throw new Error('登录已过期') }
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<T>
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthResult {
  access_token: string
  token_type: string
  role: string
  username: string
}

export async function login(username: string, password: string): Promise<AuthResult> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return ok(res)
}

export async function register(username: string, password: string): Promise<AuthResult> {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return ok(res)
}

export async function getMe() {
  const res = await fetch(`${BASE}/auth/me`, { headers: authHeaders() })
  return ok<{ user_id: string; username: string; role: string; created_at: number }>(res)
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export async function listSessions() {
  const res = await fetch(`${BASE}/sessions`, { headers: authHeaders() })
  return ok<{ sessions: Array<{ session_id: string; title: string; created_at: number; last_active: number }> }>(res)
}

export async function getSessionMessages(sessionId: string) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`, { headers: authHeaders() })
  return ok<{
    session_id: string
    messages: Array<{ id: number; role: string; content: string; created_at: number }>
  }>(res)
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (res.status === 401) { handle401(); throw new Error('登录已过期') }
  if (!res.ok && res.status !== 204) throw new Error(await parseError(res))
}

// ── Documents ─────────────────────────────────────────────────────────────────

export async function listDocuments() {
  const res = await fetch(`${BASE}/documents`, { headers: authHeaders() })
  return ok<Array<{ doc_id: string; filename: string; chunk_count: number; uploaded_at: number }>>(res)
}

export async function uploadDocument(file: File) {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/documents`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  return ok<{ filename: string; chunks_added: number; message: string }>(res)
}

export async function deleteDocument(docId: string) {
  const res = await fetch(`${BASE}/documents/${docId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  return ok<{ deleted_count: number; message: string }>(res)
}

// ── SSE streaming chat ────────────────────────────────────────────────────────

export async function* streamChat(
  question: string,
  sessionId: string | null,
  ragMode: string,
): AsyncGenerator<SSEEvent> {
  const token = getToken()
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, session_id: sessionId, rag_mode: ragMode }),
  })

  if (res.status === 401) { handle401(); return }
  if (!res.ok || !res.body) throw new Error(await parseError(res))

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  let eventType = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })

    const lines = buf.split('\n')
    buf = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6)) as Record<string, unknown>
          yield { type: eventType as SSEEvent['type'], data }
        } catch { /* skip malformed lines */ }
        eventType = ''
      }
    }
  }
}
