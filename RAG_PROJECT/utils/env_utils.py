from core.config import get_settings

_s = get_settings()

OPENAI_API_KEY = _s.openai_api_key
DEEPSEEK_API_KEY = _s.deepseek_api_key
MILVUS_URI = _s.milvus_uri
COLLECTION_NAME = _s.milvus_collection
