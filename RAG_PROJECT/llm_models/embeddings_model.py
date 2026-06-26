from core.config import get_settings
from utils.log_utils import log
import os

_s = get_settings()

bge_embedding = None

# 配置 HuggingFace 镜像源（使用国内镜像加速下载）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 先尝试使用 OpenAI embeddings（如果可用）
if _s.openai_api_key:
    try:
        from langchain_openai import OpenAIEmbeddings
        log.info("尝试使用 OpenAI Embeddings")
        bge_embedding = OpenAIEmbeddings(
            api_key=_s.openai_api_key,
            base_url=_s.openai_base_url,
            model="text-embedding-3-small"
        )
        log.info("OpenAI Embeddings 加载成功")
    except Exception as e:
        log.warning(f"OpenAI Embeddings 加载失败: {e}")

# 如果 OpenAI 不行，尝试 HuggingFace（使用镜像源）
if bge_embedding is None:
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        log.info(f"尝试从 HuggingFace 镜像下载并加载模型: {_s.bge_model_name}")
        bge_embedding = HuggingFaceEmbeddings(
            model_name=_s.bge_model_name,
            model_kwargs={"device": _s.bge_device},
            encode_kwargs={"normalize_embeddings": True},
        )
        log.info("HuggingFace Embeddings 加载成功！")
    except Exception as e:
        log.error(f"HuggingFace Embeddings 加载失败: {e}")
        log.warning("将使用 Mock Embeddings 作为备用")

# 最后的备选方案
if bge_embedding is None:
    from langchain_core.embeddings import Embeddings
    class MockEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [[0.0]*512 for _ in texts]
        def embed_query(self, text):
            return [0.0]*512
    bge_embedding = MockEmbeddings()
    log.warning("使用 Mock Embeddings（备用）")
