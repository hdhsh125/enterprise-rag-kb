from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm_models.all_llm import llm
from utils.log_utils import log

_ROLE_MAP = {"human": "human", "ai": "assistant", "assistant": "assistant"}


async def generate(state):
    question = state["question"]
    documents = state.get("documents") or []
    chat_history = state.get("chat_history") or []

    def format_docs(docs):
        if isinstance(docs, list):
            return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content'))
        elif hasattr(docs, 'page_content'):
            return docs.page_content
        return ""

    context = format_docs(documents)

    # Build messages: system -> prior turns -> current question
    history_tuples = [
        (_ROLE_MAP.get(msg.type, "human"), msg.content)
        for msg in chat_history
    ]

    messages = [
        (
            "system",
            "你是一个问答任务助手。请根据以下检索到的上下文内容回答问题。"
            "如果不知道答案，请直接说明。回答保持简洁。\n\n上下文：\n{context}",
        ),
        *history_tuples,
        ("human", "{question}"),
    ]

    prompt = ChatPromptTemplate.from_messages(messages)
    rag_chain = prompt | llm | StrOutputParser()

    generation = ""
    try:
        async for chunk in rag_chain.astream({"context": context, "question": question}):
            generation += chunk
    except Exception as e:
        log.error(f"[generate] LLM 调用失败: {e}")
        generation = "抱歉，生成回答时出现错误，请稍后重试。"

    return {"documents": documents, "question": question, "generation": generation}