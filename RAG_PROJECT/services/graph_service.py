"""GraphService — async wrapper around the two LangGraph RAG workflows.

Dispatch logic:
  rag_mode="basic"                     → Graph 1 (Agent-ToolNode basic loop)
  rag_mode="auto"|"vectorstore"|"web_search" → Graph 2 (Corrective RAG)
"""
import asyncio
import json
from typing import AsyncGenerator, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage

from services import chat_store
from services.session_store import session_store
from utils.log_utils import log

RagMode = Literal["basic", "auto", "vectorstore", "web_search"]

# ── Node label maps ───────────────────────────────────────────────────────────

_GRAPH1_LABELS: dict[str, str] = {
    "__start__": "开始处理...",
    "agent":     "智能体自主决策中...",
    "retrieve":  "正在从知识库检索文档...",
    "rewrite":   "正在重写查询语句...",
    "generate":  "正在生成回答...",
}

_GRAPH2_LABELS: dict[str, str] = {
    "__start__":       "开始处理...",
    "route_question":  "正在分析问题类型...",
    "retrieve":        "正在从知识库检索相关文档...",
    "web_search":      "正在进行网络搜索...",
    "grade_documents": "正在评估文档相关性...",
    "transform_query": "正在优化查询语句...",
    "generate":        "正在生成回答...",
}


# ── Session helpers ───────────────────────────────────────────────────────────

def _get_or_create_session(session_id: Optional[str], user_id: str):
    """Return (sid, MemSession), rehydrating from SQLite if evicted from memory."""
    if session_id:
        mem = session_store.get_session(session_id)
        if mem:
            return session_id, mem
        db = chat_store.get_session(session_id)
        if db:
            if db.user_id != user_id:
                raise PermissionError(f"用户无权访问会话 {session_id}")
            sid, mem = session_store.get_or_create(session_id)
            mem.history = chat_store.get_history_as_messages(session_id)
            mem.last_active = db.last_active
            return sid, mem

    sid, mem = session_store.get_or_create(None)
    chat_store.create_session(user_id=user_id, session_id=sid)
    return sid, mem


def _build_graph1_input(question: str, history: list) -> dict:
    """Convert session history → AgentState messages for graph1."""
    return {"messages": list(history) + [HumanMessage(content=question)]}


def _extract_graph1_answer(result: dict) -> str:
    """Extract last AIMessage from graph1 output."""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return ""


# ── Service ───────────────────────────────────────────────────────────────────

class GraphService:
    """Async façade over the two synchronous LangGraph workflows."""

    # ── Non-streaming invoke ─────────────────────────────────────────────────

    async def invoke(
        self,
        question: str,
        user_id: str,
        session_id: Optional[str] = None,
        rag_mode: RagMode = "auto",
    ) -> dict:
        try:
            sid, session = _get_or_create_session(session_id, user_id)
        except PermissionError as e:
            return {"answer": str(e), "session_id": session_id or ""}

        log.info(f"invoke  session={sid}  mode={rag_mode}  q={question[:80]!r}")
        loop = asyncio.get_running_loop()

        if rag_mode == "basic":
            from graph.graph1_api import graph as g1
            inputs = _build_graph1_input(question, list(session.history))
            result = await loop.run_in_executor(None, g1.invoke, inputs)
            answer = _extract_graph1_answer(result)
        else:
            from graph2.graph_2 import graph as g2
            inputs = {
                "question": question,
                "chat_history": list(session.history),
                "transform_count": 0,
                "rag_mode": rag_mode,
            }
            result = await loop.run_in_executor(None, g2.invoke, inputs)
            answer = result.get("generation", "")

        session_store.append_turn(sid, question, answer)
        chat_store.append_turn(sid, question, answer)
        return {"answer": answer, "session_id": sid}

    # ── SSE streaming invoke ─────────────────────────────────────────────────

    async def invoke_stream(
        self,
        question: str,
        user_id: str,
        session_id: Optional[str] = None,
        rag_mode: RagMode = "auto",
    ) -> AsyncGenerator[str, None]:
        try:
            sid, session = _get_or_create_session(session_id, user_id)
        except PermissionError as e:
            yield _sse("error", {"message": str(e)})
            return

        log.info(f"stream  session={sid}  mode={rag_mode}  q={question[:80]!r}")

        if rag_mode == "basic":
            gen = self._stream_graph1(question, session, sid, rag_mode)
        else:
            gen = self._stream_graph2(question, session, sid, rag_mode)

        async for chunk in gen:
            yield chunk

    # ── Graph 1 streaming ────────────────────────────────────────────────────

    async def _stream_graph1(self, question, session, sid, rag_mode):
        from graph.graph1_api import graph as g1
        inputs = _build_graph1_input(question, list(session.history))

        answer = ""
        current_node: Optional[str] = None
        seen_nodes: set[str] = set()

        try:
            async for event in g1.astream_events(inputs, version="v2"):
                kind = event.get("event", "")
                meta = event.get("metadata", {})
                lg_node = meta.get("langgraph_node", "")

                if kind == "on_chain_start":
                    name = event.get("name", "")
                    if name in _GRAPH1_LABELS and name not in seen_nodes:
                        current_node = name
                        seen_nodes.add(name)
                        yield _sse("node_start", {"node": name, "label": _GRAPH1_LABELS[name]})

                elif kind == "on_chat_model_stream":
                    if lg_node == "generate":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str):
                            answer += chunk.content
                            yield _sse("token", {"token": chunk.content})

                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    if name == current_node:
                        yield _sse("node_complete", {"node": name})

            if not answer:
                log.info("[graph1] No tokens captured, falling back to invoke")
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, g1.invoke, inputs)
                answer = _extract_graph1_answer(result)

            yield _sse("sources", {"documents": []})
            session_store.append_turn(sid, question, answer)
            chat_store.append_turn(sid, question, answer)
            yield _sse("done", {"session_id": sid, "rag_mode": rag_mode, "answer": answer})

        except Exception as exc:
            log.error(f"[graph1] stream error: {exc}")
            yield _sse("error", {"message": str(exc)})

    # ── Graph 2 streaming ────────────────────────────────────────────────────

    async def _stream_graph2(self, question, session, sid, rag_mode):
        from graph2.graph_2 import graph as g2
        inputs = {
            "question": question,
            "chat_history": list(session.history),
            "transform_count": 0,
            "rag_mode": rag_mode,
        }

        answer = ""
        current_node: Optional[str] = None
        seen_nodes: set[str] = set()
        documents = []

        try:
            async for event in g2.astream_events(inputs, version="v2"):
                kind = event.get("event", "")
                meta = event.get("metadata", {})
                lg_node = meta.get("langgraph_node", "")

                if kind == "on_chain_start":
                    name = event.get("name", "")
                    if name in _GRAPH2_LABELS and name not in seen_nodes:
                        current_node = name
                        seen_nodes.add(name)
                        yield _sse("node_start", {"node": name, "label": _GRAPH2_LABELS[name]})

                elif kind == "on_chat_model_stream":
                    if lg_node == "generate":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str):
                            answer += chunk.content
                            yield _sse("token", {"token": chunk.content})

                elif kind == "on_chain_end":
                    name = event.get("name", "")
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "documents" in output:
                        docs = output["documents"]
                        if isinstance(docs, list):
                            documents = docs
                        elif hasattr(docs, "page_content"):
                            documents = [docs]
                    if name == current_node:
                        yield _sse("node_complete", {"node": name})

            if not answer:
                log.info("[graph2] No tokens captured, falling back to invoke")
                loop = asyncio.get_running_loop()
                final = await loop.run_in_executor(None, g2.invoke, inputs)
                answer = final.get("generation", "")
                documents = final.get("documents", [])

            yield _sse("sources", {"documents": _extract_sources(documents)})
            session_store.append_turn(sid, question, answer)
            chat_store.append_turn(sid, question, answer)
            yield _sse("done", {"session_id": sid, "rag_mode": rag_mode, "answer": answer})

        except Exception as exc:
            log.error(f"[graph2] stream error: {exc}")
            yield _sse("error", {"message": str(exc)})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_sources(documents: list) -> list[dict]:
    sources = []
    for doc in (documents or []):
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        preview = content[:200].replace("\n", " ") if content else ""
        sources.append({
            "title": meta.get("title", meta.get("filename", meta.get("source", "未知来源"))),
            "category": meta.get("category", ""),
            "preview": preview + ("..." if len(content) > 200 else ""),
        })
    return sources


graph_service = GraphService()
