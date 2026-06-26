"""RAG Project 入口 —— 启动 FastAPI 服务。"""

import uvicorn
from app import app
from core.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "app:app",
        host=s.api_host,
        port=s.api_port,
        reload=False,
        log_level=s.log_level.lower(),
    )