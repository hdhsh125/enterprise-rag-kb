from fastapi import APIRouter
from api.schemas import HealthResponse
from core.config import get_settings

router = APIRouter(tags=["ops"])


@router.get("/health", response_model=HealthResponse)
async def health():
    s = get_settings()
    milvus_ok = False
    for uri in [s.milvus_uri, "milvus_lite.db"]:
        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=uri)
            client.list_collections()
            milvus_ok = True
            break
        except Exception:
            pass

    return HealthResponse(
        status="ok" if milvus_ok else "degraded",
        version="1.0.0",
        milvus_connected=milvus_ok,
        llm_model=s.deepseek_model,
    )
