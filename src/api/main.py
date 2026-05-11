"""
ReviewScope - FastAPI application entrypoint.

Layered architecture:

    api      <- FastAPI routers (this package)
    services <- business logic, orchestration
    database <- Supabase client wrappers
    schemas  <- pydantic request/response models
    nlp      <- NLP pipeline (ABSA, summary)
    models   <- low-level ML model wrappers (BERT/BERTopic/KeyBERT)
    parsers  <- CSV / Excel / Google Takeout JSON
"""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is importable
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import settings  # noqa: E402
from src.api.routes import analyses, exports, me, projects  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    force=True,
)
# explicitly set INFO for our pipeline modules
for name in ("src", "src.nlp", "src.models", "src.services"):
    logging.getLogger(name).setLevel(logging.INFO)
logger = logging.getLogger("reviewscope")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ReviewScope API",
        description="Intelligent web platform for NLP-based customer review analysis.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    _cors_kw: dict = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    _origins = settings.cors_origins_list
    _regex = settings.cors_origin_regex.strip()
    if _origins:
        _cors_kw["allow_origins"] = _origins
    if _regex:
        _cors_kw["allow_origin_regex"] = _regex
    if "allow_origins" not in _cors_kw and "allow_origin_regex" not in _cors_kw:
        _cors_kw["allow_origins"] = ["http://localhost:3000"]
    app.add_middleware(CORSMiddleware, **_cors_kw)

    app.include_router(me.router)
    app.include_router(projects.router)
    app.include_router(analyses.router)
    app.include_router(exports.router)

    @app.get("/")
    def root():
        return {
            "name": "ReviewScope API",
            "version": "2.0.0",
            "docs": "/docs",
        }

    @app.get("/api/health")
    def health():
        return {
            "status": "healthy",
            "supabase_configured": bool(settings.supabase_url),
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
