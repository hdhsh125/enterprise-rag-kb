import { create } from 'zustand'
import type { ChatSession, DisplayMessage, SourceDocument, RagMode, WorkflowNode } from '../types'

// ── Workflow node templates ───────────────────────────────────────────────────

const GRAPH1_NODES: WorkflowNode[] = [
  { name: 'agent',    label: '智能体自主决策', status: 'idle' },
  { name: 'retrieve', label: '知识库检索',     status: 'idle' },
  { name: 'rewrite',  label: '查询重写优化',   status: 'idle' },
  { name: 'generate', label: '回答生成',       status: 'idle' },
]

const GRAPH2_NODES: WorkflowNode[] = [
  { name: 'route_question',  label: '问题分析与路由',   status: 'idle' },
  { name: 'retrieve',        label: '知识库检索',       status: 'idle' },
  { name: 'web_search',      label: '网络搜索',         status: 'idle' },
  { name: 'grade_documents', label: '文档相关性评估',   status: 'idle' },
  { name: 'transform_query', label: '查询优化重写',     status: 'idle' },
  { name: 'generate',        label: '回答生成',         status: 'idle' },
]

function freshNodes(mode: RagMode): WorkflowNode[] {
  return (mode === 'basic' ? GRAPH1_NODES : GRAPH2_NODES).map(n => ({ ...n }))
}

// ── Store definition ─────────────────────────────────────────────────────────

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: DisplayMessage[]
  ragMode: RagMode
  sending: boolean
  workflowNodes: WorkflowNode[]
  sources: SourceDocument[]

  // Session actions
  setSessions: (sessions: ChatSession[]) => void
  setCurrentSession: (id: string | null) => void

  // Message actions
  setMessages: (msgs: DisplayMessage[]) => void
  appendMessage: (msg: DisplayMessage) => void
  /** Append a token to the last assistant message during SSE streaming */
  appendToken: (token: string) => void
  /** Finalise the last assistant message (clear isStreaming, set definitive content) */
  finalizeAssistant: (content: string) => void

  // Mode
  setRagMode: (mode: RagMode) => void

  // Streaming state
  setSending: (v: boolean) => void

  // Workflow
  activateNode: (name: string) => void
  allNodesDone: () => void
  resetWorkflow: () => void

  // Sources
  setSources: (sources: SourceDocument[]) => void
}

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  ragMode: 'auto',
  sending: false,
  workflowNodes: freshNodes('auto'),
  sources: [],

  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (id) => set({ currentSessionId: id }),

  setMessages: (msgs) => set({ messages: msgs }),

  appendMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  appendToken: (token) =>
    set((s) => {
      const msgs = [...s.messages]
      const idx = msgs.length - 1
      if (idx >= 0 && msgs[idx].role === 'assistant') {
        msgs[idx] = { ...msgs[idx], content: msgs[idx].content + token, isStreaming: true }
      }
      return { messages: msgs }
    }),

  finalizeAssistant: (content) =>
    set((s) => {
      const msgs = [...s.messages]
      const idx = msgs.length - 1
      if (idx >= 0 && msgs[idx].role === 'assistant') {
        msgs[idx] = { ...msgs[idx], content, isStreaming: false }
      }
      return { messages: msgs }
    }),

  setRagMode: (mode) =>
    set({ ragMode: mode, workflowNodes: freshNodes(mode) }),

  setSending: (v) => set({ sending: v }),

  activateNode: (name) =>
    set((s) => ({
      workflowNodes: s.workflowNodes.map((n) => {
        if (n.status === 'active') return { ...n, status: 'done' as const }
        if (n.name === name)      return { ...n, status: 'active' as const }
        return n
      }),
    })),

  allNodesDone: () =>
    set((s) => ({
      workflowNodes: s.workflowNodes.map((n) =>
        n.status === 'active' ? { ...n, status: 'done' as const } : n
      ),
    })),

  resetWorkflow: () =>
    set((s) => ({ workflowNodes: freshNodes(s.ragMode), sources: [] })),

  setSources: (sources) => set({ sources }),
}))
