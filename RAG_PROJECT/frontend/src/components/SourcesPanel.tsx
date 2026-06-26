import { Tag, Typography } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'
import { useChatStore } from '../store/chatStore'

const { Text, Paragraph } = Typography

export default function SourcesPanel() {
  const sources = useChatStore((s) => s.sources)

  if (!sources.length) return null

  return (
    <div style={{ padding: '14px 16px', borderBottom: '1px solid #f0f0f0' }}>
      <Text
        style={{
          fontSize: 11,
          color: '#888',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          fontWeight: 600,
          display: 'block',
          marginBottom: 10,
        }}
      >
        📄 引用来源
      </Text>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sources.map((src, i) => (
          <div
            key={i}
            style={{
              background: '#f8f9fb',
              border: '1px solid #eef0f4',
              borderRadius: 8,
              padding: '9px 12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
              <FileTextOutlined style={{ color: '#4f8cff', fontSize: 11 }} />
              <Text strong style={{ fontSize: 12, color: '#1a1a2e' }}>
                {src.title}
              </Text>
              {src.category && (
                <Tag style={{ fontSize: 10, padding: '0 5px', lineHeight: '16px', marginLeft: 2 }}>
                  {src.category}
                </Tag>
              )}
            </div>
            <Paragraph
              ellipsis={{ rows: 3 }}
              style={{ fontSize: 12, color: '#777', margin: 0, lineHeight: 1.5 }}
            >
              {src.preview}
            </Paragraph>
          </div>
        ))}
      </div>
    </div>
  )
}
