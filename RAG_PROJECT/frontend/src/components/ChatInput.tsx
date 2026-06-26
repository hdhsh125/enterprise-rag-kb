import { useState } from 'react'
import { Button, Input } from 'antd'
import { SendOutlined } from '@ant-design/icons'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')

  function handleSend() {
    const q = text.trim()
    if (!q || disabled) return
    onSend(q)
    setText('')
  }

  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
      <Input.TextArea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
          }
        }}
        placeholder="请输入你的问题… (Enter 发送，Shift+Enter 换行)"
        autoSize={{ minRows: 1, maxRows: 5 }}
        style={{ flex: 1, borderRadius: 12, resize: 'none' }}
        disabled={disabled}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        loading={disabled}
        style={{
          height: 40,
          padding: '0 20px',
          borderRadius: 12,
          background: '#1a1a2e',
          borderColor: '#1a1a2e',
          flexShrink: 0,
        }}
      >
        发送
      </Button>
    </div>
  )
}
