from fastapi import APIRouter, Depends, HTTPException

from api.deps import require_user
from api.schemas import (
    SessionInfo,
    ChatSessionListResponse,
    ChatSessionItem,
    ChatMessagesResponse,
    ChatMessageItem,
)
from services import chat_store, session_store
from services.user_store import User

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=ChatSessionListResponse)
async def list_sessions(user: User = Depends(require_user)):
    """获取当前用户的所有会话列表。"""
    sessions = chat_store.list_sessions(user.user_id)
    return ChatSessionListResponse(
        sessions=[
            ChatSessionItem(
                session_id=s.session_id,
                title=s.title,
                created_at=s.created_at,
                last_active=s.last_active,
            )
            for s in sessions
        ]
    )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str, user: User = Depends(require_user)):
    """获取会话信息（从持久化存储读取，含归属权校验）。"""
    sess = chat_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    # 从持久化存储计算消息数
    messages = chat_store.get_messages(session_id)
    turn_count = sum(1 for m in messages if m.role == "user")
    return SessionInfo(
        session_id=sess.session_id,
        created_at=sess.created_at,
        last_active=sess.last_active,
        turn_count=turn_count,
    )


@router.get("/{session_id}/messages", response_model=ChatMessagesResponse)
async def get_session_messages(session_id: str, user: User = Depends(require_user)):
    """获取会话的所有消息。"""
    sess = chat_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    messages = chat_store.get_messages(session_id)
    return ChatMessagesResponse(
        session_id=session_id,
        messages=[
            ChatMessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, user: User = Depends(require_user)):
    """删除会话及其所有消息。"""
    sess = chat_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权删除此会话")
    # 同时删除内存中的会话和持久化的会话
    session_store.delete_session(session_id)
    chat_store.delete_session(session_id)
