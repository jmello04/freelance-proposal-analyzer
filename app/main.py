from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.analysis import router as analysis_router
from app.core.config import settings
from app.infra.database.connection import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    try:
        await init_db()
        logger.info("Aplicação pronta.")
    except Exception as exc:
        logger.critical("Falha crítica na inicialização: %s", exc)
        raise
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(analysis_router)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def servir_frontend() -> FileResponse:
    if not os.path.isfile(INDEX_HTML):
        return JSONResponse(
            status_code=503,
            content={"detail": "Interface não encontrada. Verifique a instalação."},
        )
    return FileResponse(INDEX_HTML)


@app.get("/health", tags=["Sistema"], summary="Verificação de saúde da aplicação")
async def health_check() -> dict:
    return {"status": "ok", "versao": settings.APP_VERSION, "app": settings.APP_NAME}


@app.exception_handler(Exception)
async def handler_erro_generico(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Erro não tratado em %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Tente novamente."},
    )
