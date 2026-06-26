import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Form, Input, Tabs, Typography } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'
import * as api from '../api/client'
import type { UserInfo } from '../types'

const { Title, Text } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form] = Form.useForm<{ username: string; password: string }>()

  async function handleSubmit(values: { username: string; password: string }) {
    setLoading(true)
    setError('')
    try {
      const data =
        mode === 'login'
          ? await api.login(values.username, values.password)
          : await api.register(values.username, values.password)

      const user: UserInfo = {
        user_id: '',
        username: data.username,
        role: data.role as 'admin' | 'user',
        created_at: Date.now() / 1000,
      }
      setAuth(data.access_token, user)

      // Fetch full user info (includes user_id) and update store
      try {
        const me = await api.getMe()
        setAuth(data.access_token, me as UserInfo)
      } catch { /* use partial info if /me fails */ }

      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
      }}
    >
      <Card
        style={{ width: 400, borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.45)' }}
        styles={{ body: { padding: '40px 36px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Title level={4} style={{ color: '#1a1a2e', margin: 0 }}>
            半导体知识库 RAG 助手
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            LangGraph · Milvus · DeepSeek
          </Text>
        </div>

        <Tabs
          activeKey={mode}
          centered
          onChange={(k) => {
            setMode(k as typeof mode)
            setError('')
            form.resetFields()
          }}
          items={[
            { key: 'login', label: '登录' },
            { key: 'register', label: '注册' },
          ]}
          style={{ marginBottom: 4 }}
        />

        {error && (
          <Alert message={error} type="error" showIcon style={{ marginBottom: 14 }} />
        )}

        <Form form={form} onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bbb' }} />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              ...(mode === 'register'
                ? [{ min: 8, message: '密码至少 8 位' }]
                : []),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bbb' }} />}
              placeholder="密码"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 44,
                fontSize: 15,
                background: '#1a1a2e',
                borderColor: '#1a1a2e',
              }}
            >
              {mode === 'login' ? '登录' : '注册'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
