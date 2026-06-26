# 企业级 RAG 智能知识库系统

面向**半导体与芯片制造**领域的企业级智能知识库问答系统，基于 RAG 架构构建。

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM | DeepSeek V4 Pro（OpenAI 兼容） |
| 向量数据库 | Milvus — BGE Dense(512维) + BM25 Sparse 混合检索，RRF 排序 |
| RAG 框架 | LangGraph + LangChain |
| 后端 | FastAPI + Python 3.12，JWT 认证，SQLite 持久化 |
| **前端** | **React 19 + TypeScript + Ant Design + Zustand** |

## 双模式 RAG 工作流

```
基础模式 (Graph v1) — Agent-ToolNode
─────────────────────────────────────
START → agent → retrieve(ToolNode) → grade_documents → generate
                     ↑                     ↓
                 rewrite ←─────────── (not relevant)

高级模式 (Graph v2) — Corrective RAG
─────────────────────────────────────
START → route_question ─→ retrieve ──→ grade_documents
             ↓                               ↓
         web_search             transform_query ←─(no docs)
             ↓                        ↓
         generate ←─────────────────────
             ↓
    hallucination check → answer quality → useful: END
                              ↓ not useful
                          transform_query
```

## 核心特性

- **双模式 RAG**：基础 Agent-ToolNode 自主决策 vs 高级 CRAG 幻觉检测
- **混合检索**：BM25 + Dense 向量 + RRF 融合排序，提升召回精度
- **语义分块**：SemanticChunker 保留文档上下文完整性
- **幻觉检测**：生成内容与检索文档的一致性二元评分
- **回答质量评估**：自动判断是否准确回答问题
- **SSE 流式输出**：实时推送节点状态 + token 级别生成
- **React 前端**：Zustand 状态管理，路由守卫，工作流可视化
- **多进程写入**：Producer-Consumer 管道支持海量文档并发入库

## 快速启动

### 1. 环境准备

```bash
# Python 3.11+
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 TAVILY_API_KEY
```

### 3. 启动 Milvus（二选一）

**方式A：Docker 启动远程 Milvus**
```bash
docker-compose -f docker-compose-milvus.yml up -d
```

**方式B：本地 Milvus Lite（自动回退）**

### 4. 导入知识库文档

将 Markdown 文档放入 `datas/md/` 目录，然后通过管理界面上传，或运行：

```bash
python documents/write_milvus.py
```

### 5. 构建前端（可选，开发模式见下）

```bash
cd frontend
npm install
npm run build          # 构建产物输出到 ../static/
cd ..
```

### 6. 启动服务

```bash
python app.py
# 或
uvicorn app:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 进入问答界面。

### 前端开发模式（热重载）

```bash
# Terminal 1: 启动后端
python app.py

# Terminal 2: 启动 Vite 开发服务器（代理到 :8000）
cd frontend
npm run dev            # http://localhost:3000
```

### Docker 部署

```bash
docker-compose up -d
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 聊天界面 |
| `/health` | GET | 健康检查 |
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/me` | GET | 获取当前用户 |
| `/api/v1/chat` | POST | 普通问答 |
| `/api/v1/chat/stream` | POST | 流式问答 (SSE) |
| `/api/v1/sessions/{id}` | GET | 获取会话信息 |
| `/api/v1/documents` | GET/POST | 文档管理 (管理员) |
| `/api/v1/documents/{id}` | DELETE | 删除文档 (管理员) |
| `/docs` | GET | Swagger API 文档 |
| `/redoc` | GET | ReDoc API 文档 |

## RAG 模式参数（`rag_mode`）

| 值 | 工作流 | 说明 |
|----|--------|------|
| `basic` | Graph v1 | Agent-ToolNode 自主决策（新增） |
| `auto` | Graph v2 | CRAG 自动路由（默认） |
| `vectorstore` | Graph v2 | 强制知识库检索 |
| `web_search` | Graph v2 | 强制 Web 搜索 |

## 项目结构

```
RAG_PROJECT/
├── api/                  # FastAPI 路由与中间件
│   ├── routers/          # auth, chat, documents, health, sessions
│   ├── deps.py           # 认证依赖
│   ├── middleware.py      # 请求追踪中间件
│   └── schemas.py         # Pydantic 数据模型
├── core/
│   └── config.py          # 配置管理 (pydantic-settings)
├── documents/
│   ├── markdown_parser.py # Markdown 解析 + 语义分块
│   ├── milvus_db.py       # Milvus 连接与集合管理
│   └── write_milvus.py    # 批量写入脚本
├── graph2/                # LangGraph 主工作流
│   ├── graph_2.py         # 图定义与路由逻辑
│   ├── graph_state2.py    # 状态定义
│   ├── retriever_node.py  # 检索节点
│   ├── grade_documents_node.py # 文档评分节点
│   ├── grade_hallucinations_chain.py # 幻觉检测链
│   ├── grade_answer_chain.py   # 回答质量评估链
│   ├── generate_node2.py  # 生成节点
│   ├── transform_query_node.py # 查询优化节点
│   ├── web_search_node.py # 网络搜索节点
│   └── query_route_chain.py # 路由决策链
├── llm_models/
│   ├── all_llm.py         # LLM 实例
│   └── embeddings_model.py # BGE Embedding 模型
├── services/
│   ├── graph_service.py   # Graph 调用服务
│   ├── session_store.py   # 会话管理
│   ├── user_store.py      # 用户管理 (SQLite)
│   └── doc_store.py       # 文档元数据管理
├── tools/
│   └── retriever_tools.py # 检索器工具
├── utils/
│   ├── security.py        # JWT + bcrypt
│   ├── log_utils.py       # 日志工具
│   └── env_utils.py       # 环境变量工具
├── frontend/              # React 19 + TypeScript 前端源码
│   ├── src/
│   │   ├── store/         # Zustand (authStore, chatStore)
│   │   ├── api/client.ts  # API 客户端 + SSE 流
│   │   ├── pages/         # LoginPage / ChatPage
│   │   └── components/    # SessionSidebar / WorkflowPanel / ...
│   └── vite.config.ts     # 构建输出 → ../static/
├── static/                # 前端构建产物（FastAPI 静态服务）
├── datas/
│   └── md/                # 知识库 Markdown 文档
├── app.py                 # 应用入口
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 默认管理员账号

- 用户名：`admin`
- 密码：`Admin@123456`