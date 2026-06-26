import { Avatar } from 'antd'
import { LoadingOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import type { DisplayMessage } from '../types'

const WELCOME_MD = `你好！我是**半导体知识库助手**，专注于半导体材料、芯片制造、光刻技术等领域。

支持四种检索模式：

| 模式 | 说明 |
|------|------|
| **基础模式** | Agent-ToolNode 自主决策检索与重写 |
| **自动路由** | CRAG 智能判断知识库或网络搜索 |
| **知识库** | 强制从企业向量库检索 |
| **网络搜索** | 强制实时互联网搜索 |`

interface Props {
  messages: DisplayMessage[]
}

export default function MessageList({ messages }: Props) {
  const displayList: DisplayMessage[] =
    messages.length === 0
      ? [{ id: 'welcome', role: 'assistant', content: WELCOME_MD }]
      : messages

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {displayList.map((msg) => (
        <div
          key={msg.id}
          className="msg-enter"
          style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            alignItems: 'flex-start',
            gap: 10,
          }}
        >
          {msg.role === 'assistant' && (
            <Avatar
              size={34}
              icon={<RobotOutlined />}
              style={{ background: '#1a1a2e', flexShrink: 0, marginTop: 2 }}
            />
          )}

          <div
            style={{
              maxWidth: '78%',
              padding: '12px 16px',
              borderRadius: 14,
              fontSize: 14,
              lineHeight: 1.75,
              ...(msg.role === 'user'
                ? {
                    background: '#1a1a2e',
                    color: '#fff',
                    borderBottomRightRadius: 4,
                  }
                : {
                    background: '#f1f3f5',
                    color: '#1a1a2e',
                    borderBottomLeftRadius: 4,
                  }),
            }}
          >
            {msg.role === 'user' ? (
              <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
            ) : msg.isStreaming && !msg.content ? (
              <span style={{ color: '#999', fontStyle: 'italic' }}>
                <LoadingOutlined style={{ marginRight: 6 }} />
                思考中...
              </span>
            ) : msg.isStreaming ? (
              // During streaming: plain text for performance
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  fontSize: 'inherit',
                  margin: 0,
                  lineHeight: 1.75,
                }}
              >
                {msg.content}
              </pre>
            ) : (
              // After streaming: full Markdown
              <MarkdownContent content={msg.content} />
            )}
          </div>

          {msg.role === 'user' && (
            <Avatar
              size={34}
              icon={<UserOutlined />}
              style={{ background: '#4f8cff', flexShrink: 0, marginTop: 2 }}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      rehypePlugins={[rehypeHighlight]}
      components={{
        p({ children }) {
          return <p style={{ margin: '5px 0' }}>{children}</p>
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        code({ className, children, ...props }: any) {
          const isBlock = Boolean(className?.includes('language-'))
          return isBlock ? (
            <code className={className} {...props}>{children}</code>
          ) : (
            <code
              style={{
                background: '#e0e4ea',
                padding: '2px 6px',
                borderRadius: 4,
                fontSize: '0.85em',
              }}
              {...props}
            >
              {children}
            </code>
          )
        },
        pre({ children }) {
          return (
            <pre
              style={{
                background: '#1e1e2e',
                borderRadius: 8,
                overflow: 'auto',
                margin: '8px 0',
                padding: '14px 18px',
                fontSize: 13,
                lineHeight: 1.55,
              }}
            >
              {children}
            </pre>
          )
        },
        table({ children }) {
          return (
            <div style={{ overflowX: 'auto', margin: '8px 0' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
                {children}
              </table>
            </div>
          )
        },
        th({ children }) {
          return (
            <th style={{ border: '1px solid #d0d5dd', padding: '6px 10px', background: '#e8ecf0', textAlign: 'left' }}>
              {children}
            </th>
          )
        },
        td({ children }) {
          return (
            <td style={{ border: '1px solid #d0d5dd', padding: '6px 10px' }}>
              {children}
            </td>
          )
        },
        blockquote({ children }) {
          return (
            <blockquote
              style={{ borderLeft: '3px solid #4f8cff', paddingLeft: 12, margin: '6px 0', color: '#666' }}
            >
              {children}
            </blockquote>
          )
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
