from langchain_community.tools import TavilySearchResults
from langchain_openai import ChatOpenAI

from core.config import get_settings

_s = get_settings()

# 构建 LLM 参数
_llm_kwargs: dict = {
    "temperature": _s.deepseek_temperature,
    "model": _s.deepseek_model,
    "api_key": _s.deepseek_api_key,
    "base_url": _s.deepseek_base_url,
}

# DeepSeek thinking 推理模式 (deepseek-v4-pro 支持)
if _s.deepseek_thinking_enabled:
    _llm_kwargs["model_kwargs"] = {
        "extra_body": {"thinking": {"type": "enabled"}},
    }

llm = ChatOpenAI(**_llm_kwargs)


def get_web_search_tool():
    """延迟初始化网络搜索工具，避免 TAVILY_API_KEY 为空时启动失败"""
    return TavilySearchResults(
        max_results=2,
        tavily_api_key=_s.tavily_api_key or None,
    )