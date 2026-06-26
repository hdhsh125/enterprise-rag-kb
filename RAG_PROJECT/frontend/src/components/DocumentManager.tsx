import { useEffect, useState } from 'react'
import { Button, List, Popconfirm, Spin, Typography, Upload, message } from 'antd'
import { DeleteOutlined, FileMarkdownOutlined, UploadOutlined } from '@ant-design/icons'
import * as api from '../api/client'
import type { DocRecord } from '../types'

const { Text } = Typography

export default function DocumentManager() {
  const [docs, setDocs] = useState<DocRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [msgApi, ctx] = message.useMessage()

  useEffect(() => { loadDocs() }, [])

  async function loadDocs() {
    setLoading(true)
    try {
      const data = await api.listDocuments()
      setDocs(data)
    } catch { /* silent */ } finally {
      setLoading(false)
    }
  }

  async function handleUpload(file: File): Promise<false> {
    setUploading(true)
    try {
      const data = await api.uploadDocument(file)
      msgApi.success(`${data.filename} 上传成功，${data.chunks_added} 个向量块`)
      loadDocs()
    } catch (err) {
      msgApi.error(err instanceof Error ? err.message : '上传失败')
    } finally {
      setUploading(false)
    }
    return false
  }

  async function handleDelete(docId: string) {
    try {
      const data = await api.deleteDocument(docId)
      msgApi.success(data.message)
      loadDocs()
    } catch (err) {
      msgApi.error(err instanceof Error ? err.message : '删除失败')
    }
  }

  return (
    <div style={{ padding: '14px 16px' }}>
      {ctx}
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
        📁 文档管理
      </Text>

      <Upload
        accept=".md,.txt"
        showUploadList={false}
        beforeUpload={handleUpload}
        disabled={uploading}
      >
        <Button
          icon={<UploadOutlined />}
          loading={uploading}
          size="small"
          block
          style={{ marginBottom: 10 }}
        >
          上传文档 (.md / .txt)
        </Button>
      </Upload>

      <Spin spinning={loading} size="small">
        {docs.length === 0 && !loading ? (
          <Text style={{ fontSize: 12, color: '#ccc' }}>暂无文档</Text>
        ) : (
          <List
            size="small"
            dataSource={docs}
            renderItem={(doc) => (
              <List.Item
                style={{ padding: '5px 0', borderBottom: '1px solid #f5f5f5' }}
                actions={[
                  <Popconfirm
                    key="del"
                    title={`确认删除「${doc.filename}」？`}
                    description="此操作将清除 Milvus 向量数据，不可恢复。"
                    onConfirm={() => handleDelete(doc.doc_id)}
                    okText="删除"
                    cancelText="取消"
                    okType="danger"
                    placement="left"
                  >
                    <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                  </Popconfirm>,
                ]}
              >
                <div style={{ flex: 1, minWidth: 0, paddingRight: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <FileMarkdownOutlined style={{ color: '#4f8cff', fontSize: 11, flexShrink: 0 }} />
                    <Text
                      style={{
                        fontSize: 12,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 140,
                        display: 'block',
                      }}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </Text>
                  </div>
                  <Text style={{ fontSize: 10, color: '#aaa' }}>
                    {doc.chunk_count} 块 ·{' '}
                    {new Date(doc.uploaded_at * 1000).toLocaleDateString('zh-CN')}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </Spin>
    </div>
  )
}
