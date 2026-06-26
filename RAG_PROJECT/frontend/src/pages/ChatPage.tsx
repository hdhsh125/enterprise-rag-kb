import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Avatar, Button, Divider, Dropdown, Layout, Space, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  LogoutOutlined, PlusOutlined, QuestionCircleOutlined, UserOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import SessionSidebar from '../components/SessionSidebar'
import MessageList from '../components/MessageList'
import ChatInput from '../components/ChatInput'
import WorkflowPanel from '../components/WorkflowPanel'
import SourcesPanel from '../components/SourcesPanel'
import DocumentManager from '../components/DocumentManager'
import * as api from '../api/client'
import type { RagMode, DisplayMessage } from '../types'

const { Header, Content, Sider } = Layout
const { Text } = Typography

const RAG_MODES: Array<{ key: RagMode; label: string; desc: string; color: string }> = [
  { key: 'basic',       label: '基础模式',   desc: 'Agent-ToolNode 自主决策检索',       color: '#722ed1' },
  { key: 'auto',        label: '自动路由',   desc: 'CRAG 智能选择知识库或网络搜索',     color: '#1677ff' },
  { key: 'vectorstore', label: '知识库',     desc: '强制从企业向量库检索',              color: '#389e0d' },
  { key: 'web_search',  label: '网络搜索',   desc: '强制实时互联网搜索',               color: '#d46b08' },
]

export default function ChatPage() {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()
  const {
    sessions, setSessions,
    currentSessionId, setCurrentSession,
    messages, setMessages, appendMessage, appendToken, finalizeAssistant,
    ragMode, setRagMode,
    sending, setSending,
    activateNode, allNodesDone, resetWorkflow,
    setSources,
  } = useChatStore()

  const [msgApi, ctx] = message.useMessage()
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load session list on mount
  useEffect(() => { loadSessions() }, [])

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadSessions() {
    try {
      const data = await api.listSessions()
      setSessions(data.sessions)
    } catch { /* silent */ }
  }

  // ── Session management ────────────────────────────────────────────────────

  async function handleSelectSession(sid: string) {
    if (sending) return
    setCurrentSession(sid)
    resetWorkflow()
    try {
      const data = await api.getSessionMessages(sid)
      const msgs: DisplayMessage[] = data.messages.map((m) => ({
        id: String(m.id),
        role: m.role as 'user' | 'assistant',
        content: m.content,
      }))
      setMessages(msgs)
    } catch {
      msgApi.error('加载历史消息失败')
    }
  }

  async function handleDeleteSession(sid: string) {
    try {
      await api.deleteSession(sid)
      if (sid === currentSessionId) {
        setCurrentSession(null)
        setMessages([])
        resetWorkflow()
      }
      await loadSessions()
    } catch (err) {
      msgApi.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  function handleNewChat() {
    setCurrentSession(null)
    setMessages([])
    resetWorkflow()
  }

  function handleLogout() {
    clearAuth()
    navigate('/login', { replace: true })
  }

  // ── Send message ──────────────────────────────────────────────────────────

  async function handleSend(question: string) {
    if (sending) return
    setSending(true)
    resetWorkflow()

    appendMessage({ id: `u-${Date.now()}`, role: 'user', content: question })
    appendMessage({ id: `a-${Date.now()}`, role: 'assistant', content: '', isStreaming: true })

    let accText = ''

    try {
      for await (const event of api.streamChat(question, currentSessionId, ragMode)) {
        switch (event.type) {
          case 'node_start':
            activateNode(event.data.node as string)
            break

          case 'token': {
            const tok = (event.data.token as string) ?? ''
            accText += tok
            appendToken(tok)
            break
          }

          case 'sources':
            setSources(
              (event.data.documents as Array<{ title: string; category: string; preview: string }>) ?? []
            )
            break

          case 'done': {
            const final = (event.data.answer as string) || accText
            finalizeAssistant(final)
            allNodesDone()
            const newSid = event.data.session_id as string
            if (newSid) setCurrentSession(newSid)
            await loadSessions()
            break
          }

          case 'error': {
            const errMsg = event.data.message as string
            finalizeAssistant(`❌ ${errMsg}`)
            allNodesDone()
            msgApi.error(errMsg)
            break
          }
        }
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : '网络错误'
      finalizeAssistant(`❌ ${errMsg}`)
      allNodesDone()
    } finally {
      setSending(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const currentMode = RAG_MODES.find((m) => m.key === ragMode)!

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      {ctx}

      {/* ── Left: Session history ─────────────────────────────────────── */}
      <Sider
        width={240}
        theme="light"
        style={{ borderRight: '1px solid #f0f0f0', overflow: 'hidden' }}
      >
        <SessionSidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelect={handleSelectSession}
          onDelete={handleDeleteSession}
          onNewChat={handleNewChat}
        />
      </Sider>

      {/* ── Center: Chat area ─────────────────────────────────────────── */}
      <Layout style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Header
          style={{
            background: '#fff',
            padding: '0 20px',
            height: 54,
            lineHeight: '54px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}
        >
          <Text strong style={{ fontSize: 15, color: '#1a1a2e' }}>
            半导体知识库 RAG 助手
          </Text>

          <Space size={8}>
            {/* RAG mode selector */}
            <Space.Compact size="small">
              {RAG_MODES.map((m) => (
                <Tooltip key={m.key} title={m.desc} placement="bottom">
                  <Button
                    size="small"
                    type={ragMode === m.key ? 'primary' : 'default'}
                    onClick={() => setRagMode(m.key)}
                    style={
                      ragMode === m.key
                        ? { background: '#1a1a2e', borderColor: '#1a1a2e' }
                        : {}
                    }
                  >
                    {m.label}
                  </Button>
                </Tooltip>
              ))}
            </Space.Compact>

            <Divider type="vertical" />

            {/* New chat */}
            <Button size="small" icon={<PlusOutlined />} onClick={handleNewChat}>
              新对话
            </Button>

            {/* User menu */}
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'info',
                    label: (
                      <div style={{ padding: '2px 0' }}>
                        <div style={{ fontWeight: 600 }}>{user?.username}</div>
                        <Tag
                          color={user?.role === 'admin' ? 'gold' : 'blue'}
                          style={{ fontSize: 11, marginTop: 2 }}
                        >
                          {user?.role === 'admin' ? '管理员' : '普通用户'}
                        </Tag>
                      </div>
                    ),
                    disabled: true,
                  },
                  { type: 'divider' },
                  {
                    key: 'logout',
                    label: '退出登录',
                    icon: <LogoutOutlined />,
                    onClick: handleLogout,
                    danger: true,
                  },
                ],
              }}
              placement="bottomRight"
            >
              <Avatar
                size={30}
                icon={<UserOutlined />}
                style={{ cursor: 'pointer', background: user?.role === 'admin' ? '#d48806' : '#1677ff' }}
              />
            </Dropdown>
          </Space>
        </Header>

        {/* Messages */}
        <Content
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px 28px 12px',
            background: '#fafafa',
          }}
        >
          <MessageList messages={messages} />
          <div ref={bottomRef} />
        </Content>

        {/* Mode indicator bar */}
        <div
          style={{
            padding: '6px 28px',
            background: '#fff',
            borderTop: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Tag color={currentMode.color} style={{ fontSize: 11 }}>
            {currentMode.label}
          </Tag>
          <Text style={{ fontSize: 11, color: '#aaa' }}>{currentMode.desc}</Text>
        </div>

        {/* Input */}
        <div
          style={{
            padding: '12px 28px 16px',
            background: '#fff',
            borderTop: '1px solid #f0f0f0',
          }}
        >
          <ChatInput onSend={handleSend} disabled={sending} />
        </div>
      </Layout>

      {/* ── Right: Workflow + Sources + Admin ─────────────────────────── */}
      <Sider
        width={300}
        theme="light"
        style={{ borderLeft: '1px solid #f0f0f0', overflowY: 'auto' }}
      >
        <div style={{ padding: '12px 16px', background: '#1a1a2e' }}>
          <Text style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>执行流程</Text>
          <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11, marginLeft: 8 }}>
            GraphRAG {ragMode === 'basic' ? 'v1' : 'v2'}
          </Text>
        </div>

        <WorkflowPanel />
        <SourcesPanel />
        {user?.role === 'admin' && <DocumentManager />}
      </Sider>
    </Layout>
  )
}
