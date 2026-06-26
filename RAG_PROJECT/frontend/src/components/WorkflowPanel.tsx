import { Typography } from 'antd'
import { CheckCircleFilled, ClockCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import { useChatStore } from '../store/chatStore'

const { Text } = Typography

const DOT_COLOR = { idle: '#d0d0d0', active: '#4f8cff', done: '#52c41a' }
const ICON = {
  idle:   <ClockCircleOutlined style={{ fontSize: 12, color: '#ccc' }} />,
  active: <LoadingOutlined style={{ fontSize: 12, color: '#4f8cff' }} spin />,
  done:   <CheckCircleFilled style={{ fontSize: 12, color: '#52c41a' }} />,
}
const MODE_LABEL: Record<string, string> = {
  basic:        '基础模式 · GraphRAG v1',
  auto:         '高级 CRAG · GraphRAG v2',
  vectorstore:  '知识库模式 · GraphRAG v2',
  web_search:   '网络搜索 · GraphRAG v2',
}

export default function WorkflowPanel() {
  const { workflowNodes, ragMode } = useChatStore()

  return (
    <div style={{ padding: '14px 16px', borderBottom: '1px solid #f0f0f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <Text style={{ fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
          ⚙ 工作流节点
        </Text>
        <Text style={{ fontSize: 10, color: '#aaa' }}>{MODE_LABEL[ragMode] ?? ragMode}</Text>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {workflowNodes.map((node) => (
          <div
            key={node.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 9,
              padding: '6px 10px',
              borderRadius: 8,
              border: `1px solid ${node.status === 'active' ? '#c5d5f8' : 'transparent'}`,
              background: node.status === 'active' ? '#f0f4ff' : 'transparent',
              transition: 'all 0.3s',
            }}
          >
            <div
              style={{
                width: 9,
                height: 9,
                borderRadius: '50%',
                background: DOT_COLOR[node.status],
                flexShrink: 0,
                animation: node.status === 'active' ? 'wf-pulse 1.2s infinite' : 'none',
              }}
            />
            <Text
              style={{
                fontSize: 12,
                color: node.status === 'idle' ? '#aaa' : '#333',
                fontWeight: node.status === 'active' ? 500 : 400,
                flex: 1,
              }}
            >
              {node.label}
            </Text>
            {ICON[node.status]}
          </div>
        ))}
      </div>
    </div>
  )
}
