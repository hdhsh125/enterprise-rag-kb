from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.middleware import RequestTracingMiddleware
from api.routers import chat, health, sessions
from api.routers import auth, documents
from core.config import get_settings
from utils.log_utils import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Startup: warming up Graph 2 workflow (loads BGE model + Milvus connection)...")
    from graph2.graph_2 import graph  # noqa: F401 — triggers module-level init
    log.info("Graph 2 workflow ready. Service is up.")
    yield
    log.info("Shutdown complete.")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Semiconductor RAG API",
        description="Enterprise knowledge-base Q&A for semiconductor / chip manufacturing domain.",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    cors_origins = s.cors_origins.split(",") if s.cors_origins != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestTracingMiddleware)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(sessions.router)
    app.include_router(documents.router)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse("static/index.html")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    s = get_settings()
    uvicorn.run(
        "app:app",
        host=s.api_host,
        port=s.api_port,
        reload=False,
        log_level=s.log_level.lower(),
    )
