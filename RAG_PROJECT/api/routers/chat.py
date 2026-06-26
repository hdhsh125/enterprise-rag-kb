from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from api.deps import require_user
from api.schemas import ChatRequest, ChatResponse
from services.graph_service import graph_service
from services.user_store import User

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, user: User = Depends(require_user)):
    request_id = getattr(request.state, "request_id", "-")
    result = await graph_service.invoke(
        question=req.question,
        user_id=user.user_id,
        session_id=req.session_id,
        rag_mode=req.rag_mode,
    )
    return ChatResponse(
        answer=result["answer"],
        session_id=result["session_id"],
        request_id=request_id,
        rag_mode=req.rag_mode,
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request, user: User = Depends(require_user)):
    """SSE 流式问答端点 —— 实时推送节点执行状态、生成令牌、来源引用。"""
    return StreamingResponse(
        graph_service.invoke_stream(
            question=req.question,
            user_id=user.user_id,
            session_id=req.session_id,
            rag_mode=req.rag_mode,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
