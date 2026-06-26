from langgraph.constants import START, END
from langgraph.graph import StateGraph

from graph2.generate_node2 import generate
from graph2.grade_answer_chain import answer_grader_chain
from graph2.grade_documents_node import grade_documents
from graph2.grade_hallucinations_chain import hallucination_grader_chain
from graph2.graph_state2 import GraphState
from graph2.query_route_chain import question_router_chain
from graph2.retriever_node import retrieve
from graph2.transform_query_node import transform_query
from graph2.web_search_node import web_search
from utils.log_utils import log


def grade_generation_v_documents_and_question(state):
    log.info("---检查生成内容是否存在幻觉---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader_chain.invoke({"documents": documents, "generation": generation})
    grade = score.binary_score

    if grade == "yes":
        log.info("---判定：生成内容基于参考文档---")
        log.info("---评估：生成回答与问题的匹配度---")
        score = answer_grader_chain.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        if grade == "yes":
            log.info("---判定：生成内容准确回答问题---")
            return "useful"
        else:
            log.info("---判定：生成内容未能准确回答问题---")
            return "not useful"
    else:
        log.info("---判定：生成内容未基于参考文档，将重新尝试---")
        return "not supported"


def decide_to_generate(state):
    log.info("---ASSESS GRADED DOCUMENTS---")
    filtered_documents = state["documents"]
    transform_count = state.get("transform_count", 0)

    if not filtered_documents:
        if transform_count >= 2:
            log.info("---决策：所有文档都与问题无关,并且已经循环了2次，转为web查询问题---")
            return "web_search"
        log.info("---决策：所有文档都与问题无关，将转换查询问题---")
        return "transform_query"
    else:
        log.info("---决策：生成最终回答---")
        return "generate"


def route_question(state):
    log.info("---ROUTE QUESTION---")
    rag_mode = state.get("rag_mode", "auto")

    # Honour forced modes without calling the LLM router
    if rag_mode == "web_search":
        log.info("---强制路由到web搜索---")
        return "web_search"
    if rag_mode == "vectorstore":
        log.info("---强制路由到RAG系统---")
        return "vectorstore"

    # Auto mode: let the LLM decide
    question = state["question"]
    source = question_router_chain.invoke({"question": question})

    if source.datasource == "web_search":
        log.info("---路由到web搜索---")
        return "web_search"
    elif source.datasource == "vectorstore":
        log.info("---路由到RAG系统---")
        return "vectorstore"


def build_graph():
    """Build and compile the Graph 2 RAG workflow. Called once at startup."""
    workflow = StateGraph(GraphState)

    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("transform_query", transform_query)

    workflow.add_conditional_edges(
        START,
        route_question,
        {
            "web_search": "web_search",
            "vectorstore": "retrieve",
        },
    )

    workflow.add_edge("web_search", "generate")
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges("grade_documents", decide_to_generate)

    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "not supported": "generate",
            "useful": END,
            "not useful": "transform_query",
        },
    )

    workflow.add_edge("transform_query", "retrieve")

    return workflow.compile()


# Module-level singleton — imported by services/graph_service.py
graph = build_graph()
