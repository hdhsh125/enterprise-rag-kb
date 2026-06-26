from graph.graph_state1 import AgentState
from llm_models.all_llm import llm
from tools.retriever_tools import get_retriever_tool
from utils.log_utils import log


# agent节点
def agent_node(state: AgentState):
    """
    调用智能体模型基于当前状态生成响应。根据问题，
    它会决定使用检索工具检索，或者直接结束。

    参数:
        state (messages): 当前状态

    返回:
        dict: 更新后的状态，包含附加到消息中的智能体响应
    """
    log.info("---开始进入工作流---")
    messages = state["messages"]

    model = llm.bind_tools([get_retriever_tool()])
    # Pass the full message history so the agent retains multi-turn context
    response = model.invoke(messages)
    return {"messages": [response]}