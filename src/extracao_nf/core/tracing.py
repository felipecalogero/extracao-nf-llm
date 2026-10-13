import os

from extracao_nf.core.config import Settings
from extracao_nf.core.logging import logger


def configurar_tracing(settings: Settings) -> bool:
    # why: pydantic-settings lê o .env sem exportá-lo; o LangChain só enxerga os.environ
    if not settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return False

    api_key = (
        settings.langsmith_api_key.get_secret_value().strip()
        if settings.langsmith_api_key is not None
        else ""
    )
    if not api_key:
        logger.warning("langsmith_desabilitado", motivo="LANGSMITH_API_KEY ausente")
        os.environ["LANGSMITH_TRACING"] = "false"
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    logger.info("langsmith_habilitado", projeto=settings.langsmith_project)
    return True
