from typing import TypedDict, List, Optional

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage


class GraphState(TypedDict):
    question: str
    generation: str
    transform_count: int
    documents: List[Document]
    chat_history: Optional[List[BaseMessage]]
    rag_mode: Optional[str]  # "auto" | "vectorstore" | "web_search"
