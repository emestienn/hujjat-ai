"""Hujjat AI: ask questions about your documents, get answers with page-level citations."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .deps import get_services
from .routes import chat, documents
from .schemas import HealthOut
from .services import Services

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"  # built frontend (Docker)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = Services.create(settings)
        logging.getLogger("hujjat").info(
            "LLM provider: %s | semantic search: %s",
            settings.resolved_provider,
            app.state.services.embedder.enabled,
        )
        yield

    app = FastAPI(
        title="Hujjat AI",
        description="Chat with your documents in Uzbek, Russian or English. "
        "Answers cite the exact file and page they came from.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(documents.router)
    app.include_router(chat.router)

    @app.get("/api/health", response_model=HealthOut, tags=["system"])
    def health(svc: Services = Depends(get_services)):
        return HealthOut(
            status="ok",
            provider=svc.provider.name,
            semantic_search=svc.embedder.enabled,
            documents=len(svc.store.list_documents()),
        )

    # In production the built React app is served from the same server.
    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Not found")
            file = STATIC_DIR / path
            if path and file.is_file():
                return FileResponse(file)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
