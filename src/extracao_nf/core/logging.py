"""Configuração de logs estruturados com structlog.

Este módulo configura o structlog para gerar logs:
- Coloridos e legíveis em desenvolvimento (ConsoleRenderer)
- Em JSON estruturado em produção (JSONRenderer)

Uso:
    from extracao_nf.core.logging import logger

    logger.info("extracao_iniciada", arquivo="nf.pdf")

Para inicializar (chamar uma única vez no startup da aplicação):
    from extracao_nf.core.logging import setup_logging
    setup_logging()
"""

import logging
import sys
from typing import cast

import structlog
from structlog.types import Processor


def _get_log_level() -> int:
    """Retorna o nível de log configurado em Settings.

    Mapeia o Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    para as constantes do módulo logging.
    """
    from extracao_nf.core.config import get_settings

    settings = get_settings()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map[settings.log_level]


def _is_development() -> bool:
    """Retorna True se o ambiente é de desenvolvimento ou teste."""
    from extracao_nf.core.config import get_settings

    settings = get_settings()
    return settings.environment in ("development", "test")


def _build_shared_processors() -> list[Processor]:
    """Retorna a lista de processors compartilhados entre dev e produção.

    Estes processors rodam para TODOS os logs, independente do ambiente.
    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


def _build_dev_processors() -> list[Processor]:
    """Retorna os processors finais de desenvolvimento (rodam após os shared).

    Inclui ConsoleRenderer (logs coloridos e legíveis) e ExceptionPrettyPrinter.
    """
    return [
        structlog.processors.ExceptionPrettyPrinter(),
        structlog.dev.ConsoleRenderer(
            colors=True,
            pad_event_to=35,
        ),
    ]


def _build_prod_processors() -> list[Processor]:
    """Retorna os processors finais de produção (rodam após os shared).

    Inclui JSONRenderer (logs em JSON estruturado, um por linha).
    """
    return [
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]


def setup_logging() -> None:
    """Inicializa o structlog e configura o logging padrão do Python.

    Deve ser chamada UMA ÚNICA VEZ no startup da aplicação (ex: no lifespan do FastAPI).

    Esta função:
    1. Configura o structlog com os processors apropriados (dev ou prod)
    2. Configura o logging padrão do Python para usar o structlog como backend
    3. Intercepta logs de bibliotecas externas (uvicorn, httpx, etc)
    4. Define o nível de log conforme Settings.log_level
    """
    is_dev = _is_development()
    log_level = _get_log_level()

    shared_processors: list[Processor] = _build_shared_processors()
    processors = _build_dev_processors() if is_dev else _build_prod_processors()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *processors,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado.

    Uso:
        logger = get_logger(__name__)
        logger.info("extracao_iniciada", arquivo="nf.pdf")

    Ou simplesmente:
        logger = get_logger()
        logger.info("mensagem")

    Args:
        name: Nome do logger (geralmente __name__). Se None, usa o root logger.

    Returns:
        BoundLogger configurado com structlog.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


# Logger global pronto para uso (importar diretamente)
# Ex: from extracao_nf.core.logging import logger
logger: structlog.stdlib.BoundLogger = structlog.get_logger()
