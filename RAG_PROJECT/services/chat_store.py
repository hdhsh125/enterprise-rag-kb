"""SQLite-backed chat history store — persistent sessions and messages."""
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain_core.messages import HumanMessage, AIMessage

DB_PATH = Path(__file__).parent.parent / "data" / "users.db"


@dataclass
class ChatSession:
    session_id: str
    user_id: str
    title: str
    created_at: float
    last_active: float


@dataclass
class ChatMessage:
    id: int
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: float


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id   TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL,
                title        TEXT NOT NULL DEFAULT '新对话',
                created_at   REAL NOT NULL,
                last_active  REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT NOT NULL,
                role         TEXT NOT NULL,
                content      TEXT NOT NULL,
                created_at   REAL NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id)"
        )
        conn.commit()
    finally:
        conn.close()


def create_session(user_id: str, session_id: Optional[str] = None, title: str = "新对话") -> ChatSession:
    """创建新会话，返回 ChatSession 对象。"""
    sid = session_id or str(uuid.uuid4())
    now = time.time()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, user_id, title, created_at, last_active) VALUES (?,?,?,?,?)",
            (sid, user_id, title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return ChatSession(sid, user_id, title, now, now)


def get_session(session_id: str) -> Optional[ChatSession]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM chat_sessions WHERE session_id=?", (session_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return ChatSession(
        session_id=row["session_id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        last_active=row["last_active"],
    )


def list_sessions(user_id: str) -> List[ChatSession]:
    """获取用户的所有会话，按最后活跃时间倒序。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_sessions WHERE user_id=? ORDER BY last_active DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        ChatSession(
            session_id=r["session_id"],
            user_id=r["user_id"],
            title=r["title"],
            created_at=r["created_at"],
            last_active=r["last_active"],
        )
        for r in rows
    ]


def append_turn(session_id: str, question: str, answer: str) -> None:
    """原子地追加一轮对话（用户问题 + 助手回答）。"""
    now = time.time()
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "user", question, now),
        )
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "assistant", answer, now),
        )
        # 更新会话最后活跃时间
        conn.execute(
            "UPDATE chat_sessions SET last_active=? WHERE session_id=?",
            (now, session_id),
        )
        # 如果是第一条用户消息，自动设置会话标题
        row = conn.execute(
            "SELECT content FROM chat_messages WHERE session_id=? AND role='user' ORDER BY created_at ASC LIMIT 1",
            (session_id,),
        ).fetchone()
        if row:
            title = row["content"][:30]
            if len(row["content"]) > 30:
                title += "..."
            conn.execute(
                "UPDATE chat_sessions SET title=? WHERE session_id=? AND title='新对话'",
                (title, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_messages(session_id: str) -> List[ChatMessage]:
    """获取会话的所有消息，按时间正序。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id=? ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        ChatMessage(
            id=r["id"],
            session_id=r["session_id"],
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def get_history_as_messages(session_id: str, max_turns: int = 10) -> list:
    """获取会话历史，转换为 LangChain BaseMessage 列表（用于 graph 输入）。

    返回 [HumanMessage, AIMessage, HumanMessage, AIMessage, ...] 格式，
    最多保留 max_turns 轮对话。
    """
    messages = get_messages(session_id)
    lc_messages = []
    for m in messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))
    # 保留最近 max_turns 轮（每轮 = 1 user + 1 assistant = 2 条消息）
    max_msgs = max_turns * 2
    if len(lc_messages) > max_msgs:
        lc_messages = lc_messages[-max_msgs:]
    return lc_messages


def delete_session(session_id: str) -> bool:
    """删除会话及其所有消息。"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM chat_sessions WHERE session_id=?", (session_id,)
        )
        conn.execute(
            "DELETE FROM chat_messages WHERE session_id=?", (session_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_session_title(session_id: str, title: str) -> None:
    """更新会话标题。"""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE chat_sessions SET title=? WHERE session_id=?",
            (title, session_id),
        )
        conn.commit()
    finally:
        conn.close()


# Initialise on import
_init_db()
