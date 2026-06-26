import { useState } from 'react'
import { Button, Popconfirm, Typography } from 'antd'
import { DeleteOutlined, MessageOutlined, PlusOutlined } from '@ant-design/icons'
import type { ChatSession } from '../types'

const { Text } = Typography

function formatTime(ts: number): string {
  const diff = Math.floor((Date.now() - ts * 1000) / 60000)
  if (diff < 1)   return '刚刚'
  if (diff < 60)  return `${diff}分钟前`
  const h = Math.floor(diff / 60)
  if (h < 24)     return `${h}小时前`
  const d = Math.floor(h / 24)
  if (d < 7)      return `${d}天前`
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}

interface Props {
  sessions: ChatSession[]
  currentSessionId: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onNewChat: () => void
}

export default function SessionSidebar({
  sessions, currentSessionId, onSelect, onDelete, onNewChat,
}: Props) {
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div
        style={{
          padding: '12px 14px',
          background: '#1a1a2e',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <Text style={{ color: '#fff', fontWeight: 600, fontSize: 13 }}>历史会话</Text>
        <Button
          size="small"
          icon={<PlusOutlined />}
          onClick={onNewChat}
          style={{
            background: 'rgba(255,255,255,0.12)',
            border: '1px solid rgba(255,255,255,0.25)',
            color: '#fff',
            fontSize: 12,
          }}
        >
          新对话
        </Button>
      </div>

      {/* Session list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {sessions.length === 0 ? (
          <div style={{ padding: '28px 16px', textAlign: 'center', color: '#bbb', fontSize: 12 }}>
            暂无历史会话
          </div>
        ) : (
          sessions.map((s) => {
            const isActive = s.session_id === currentSessionId
            const isHover = hovered === s.session_id
            return (
              <div
                key={s.session_id}
                className="session-item"
                onClick={() => onSelect(s.session_id)}
                onMouseEnter={() => setHovered(s.session_id)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '9px 14px',
                  cursor: 'pointer',
                  borderLeft: `3px solid ${isActive ? '#4f8cff' : 'transparent'}`,
                  background: isActive ? '#f0f4ff' : isHover ? '#f5f7fa' : 'transparent',
                  transition: 'background 0.15s',
                  gap: 8,
                }}
              >
                <MessageOutlined style={{ color: isActive ? '#4f8cff' : '#ccc', flexShrink: 0, fontSize: 12 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      color: isActive ? '#1a1a2e' : '#444',
                      fontWeight: isActive ? 500 : 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {s.title}
                  </div>
                  <div style={{ fontSize: 11, color: '#bbb', marginTop: 1 }}>
                    {formatTime(s.last_active)}
                  </div>
                </div>
                <Popconfirm
                  title="确认删除此会话？"
                  description="此操作不可恢复。"
                  onConfirm={(e) => { e?.stopPropagation(); onDelete(s.session_id) }}
                  onCancel={(e) => e?.stopPropagation()}
                  okText="删除"
                  cancelText="取消"
                  okType="danger"
                >
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    className="del-session-btn"
                    style={{ opacity: isHover ? 1 : 0, flexShrink: 0, transition: 'opacity 0.15s' }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
