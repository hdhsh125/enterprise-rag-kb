from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserInfo(BaseModel):
    user_id: str
    username: str
    role: str
    created_at: float


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，不传则创建新会话")
    rag_mode: Literal["basic", "auto", "vectorstore", "web_search"] = Field(
        "auto",
        description=(
            "RAG检索模式：basic=基础Agent-ToolNode模式(graph1); "
            "auto=CRAG自动路由; vectorstore=强制知识库; web_search=强制网络搜索"
        ),
    )


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    request_id: str
    rag_mode: str


# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionInfo(BaseModel):
    session_id: str
    created_at: float
    last_active: float
    turn_count: int


class ChatSessionItem(BaseModel):
    session_id: str
    title: str
    created_at: float
    last_active: float


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionItem]


class ChatMessageItem(BaseModel):
    id: int
    role: str
    content: str
    created_at: float


class ChatMessagesResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageItem]


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_added: int
    message: str


class DocumentListItem(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    uploaded_at: float


class DocumentDeleteResponse(BaseModel):
    deleted_count: int
    message: str


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    milvus_connected: bool
    llm_model: str
