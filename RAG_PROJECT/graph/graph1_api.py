"""Graph 1 — Basic RAG: Agent-ToolNode self-decision loop (API wrapper).

Architecture:
  START → agent → retrieve (ToolNode) | END
               ↓
         grade_documents → generate | rewrite → agent

Differences from graph/graph1.py:
  - No CLI while-loop; exports build_graph() + module-level singleton.
  - Uses full message history in agent_node (multi-turn awareness).
"""
from typing import Literal

from langchain_core.prompts import PromptTemplate
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from graph.agent_node import agent_node
from graph.generate_node import generate
from graph.get_human_message import get_last_human_message
from graph.graph_state1 import AgentState, Grade
from graph.rewrite_node import rewrite
from llm_models.all_llm import llm
from tools.retriever_tools import get_retriever_tool
from utils.log_utils import log


def _grade_documents(state) -> Literal["generate", "rewrite"]:
    """Decide whether retrieved docs are relevant; route to generate or rewrite."""
    log.info("---[基础模式] 评估文档相关性---")
    llm_structured = llm.with_structured_output(Grade, method="json_mode")
    prompt = PromptTemplate(
        template=(
            "你是一个评估检索文档与用户问题相关性的评分器。\n"
            "这是检索到的文档：\n\n {context} \n\n"
            "这是用户的问题：{question} \n"
            "如果文档包含与用户问题相关的关键词或语义含义，则评为相关。\n"
            "给出二元评分 'yes' 或 'no' 来表示文档是否与问题相关。"
        ),
        input_variables=["context", "question"],
    )
    chain = prompt | llm_structured
    messages = state["messages"]
    question = get_last_human_message(messages).content
    docs = messages[-1].content
    result = chain.invoke({"question": question, "context": docs})
    if result.binary_score == "yes":
        log.info("---[基础模式] 文档相关，进入生成节点---")
        return "generate"
    log.info("---[基础模式] 文档不相关，重写查询---")
    return "rewrite"


def build_graph():
    """Build and compile Graph 1 (Basic Agent-ToolNode RAG)."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("retrieve", ToolNode([get_retriever_tool()]))
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("generate", generate)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "retrieve", END: END},
    )
    workflow.add_conditional_edges("retrieve", _grade_documents)
    workflow.add_edge("rewrite", "agent")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Module-level singleton — lazy-loaded on first request via graph_service
graph = build_graph()
