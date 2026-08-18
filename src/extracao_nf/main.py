"""Ponto de entrada da aplicação FastAPI.

Este módulo inicializa o app FastAPI, registra as rotas e configura o lifespan
(startup/shutdown).

Para rodar o servidor:
    uvicorn extracao_nf.main:app --reload

Ou via Makefile:
    make run
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from extracao_nf.api.routes.health import router as health_router
from extracao_nf.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Context manager para startup e shutdown do app.

    Startup:
        - Inicializa o structlog (logs estruturados)

    Shutdown:
        - Encerra a aplicação de forma ordenada
    """
    setup_logging()
    logger.info("iniciando aplicação")

    yield

    logger.info("finalizando aplicação")


app = FastAPI(
    title="Extração NF com LLM",
    description="API de extração de dados de Nota Fiscal via LangChain e LLM",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
