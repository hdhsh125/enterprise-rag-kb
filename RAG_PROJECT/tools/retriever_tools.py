from langchain_core.tools import create_retriever_tool
from documents.milvus_db import MilvusVectorSave
from utils.log_utils import log

_mv = None
_retriever = None
_retriever_tool = None


def _init_retriever():
    global _mv, _retriever, _retriever_tool
    if _mv is not None:
        return
    try:
        _mv = MilvusVectorSave()
        _mv.create_connection()
        _retriever = _mv.vector_store_saved.as_retriever(
            search_type='similarity',
            search_kwargs={
                "k": 4,
                "score_threshold": 0.1,
                "ranker_type": "rrf",
                "ranker_params": {"k": 100},
                'filter': {"category": "content"}
            }
        )
        _retriever_tool = create_retriever_tool(
            _retriever,
            'rag_retriever',
            '搜索并返回关于 \'半导体和芯片\' 的信息, 内容涵盖：半导体和芯片的封装、测试、光刻胶等'
        )
        log.info("Milvus连接成功，检索器初始化完成")
    except Exception as e:
        log.warning(f"Milvus连接失败: {e}，检索功能不可用")
        raise


def get_retriever():
    _init_retriever()
    return _retriever


def get_retriever_tool():
    _init_retriever()
    return _retriever_tool