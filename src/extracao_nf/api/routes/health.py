"""Endpoint de health check.

Este endpoint é usado por orquestradores e load balancers para verificar se o
serviço está saudável.
"""

from fastapi import APIRouter

from extracao_nf.core.logging import logger

router = APIRouter(tags=["Saúde"])


@router.get(
    "/health",
    summary="Health check",
    description="Verifica se o serviço está saudável.",
    response_description="Status do serviço",
)
async def health() -> dict[str, str]:
    """Retorna o status do serviço.

    Returns:
        Dict com status "ok" se o serviço está saudável.
    """
    logger.info("health check endpoint")
    return {"status": "ok"}
