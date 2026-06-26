import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from core.config import get_settings


@dataclass
class Session:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    history: List[BaseMessage] = field(default_factory=list)


class SessionStore:
    """Thread-safe in-memory session store with TTL eviction."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        s = get_settings()
        self._ttl = s.session_ttl_seconds
        self._max_turns = s.max_history_turns

    def get_or_create(self, session_id: Optional[str]) -> Tuple[str, Session]:
        self._evict_expired()
        if session_id and session_id in self._sessions:
            s = self._sessions[session_id]
            s.last_active = time.time()
            return session_id, s
        new_id = session_id or str(uuid.uuid4())
        self._sessions[new_id] = Session(session_id=new_id)
        return new_id, self._sessions[new_id]

    def get_session(self, session_id: str) -> Optional[Session]:
        self._evict_expired()
        return self._sessions.get(session_id)

    def append_turn(self, session_id: str, question: str, answer: str) -> None:
        s = self._sessions.get(session_id)
        if not s:
            return
        s.history.append(HumanMessage(content=question))
        s.history.append(AIMessage(content=answer))
        max_msgs = self._max_turns * 2
        if len(s.history) > max_msgs:
            s.history = s.history[-max_msgs:]
        s.last_active = time.time()

    def delete_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._sessions.items() if now - v.last_active > self._ttl]
        for k in expired:
            del self._sessions[k]


session_store = SessionStore()
