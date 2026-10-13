"""Configurações da aplicação (lê variáveis de ambiente)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente.

    A ordem de precedência (da maior para a menor) é:
    1. Variáveis de ambiente do sistema
    2. Arquivo .env (se existir)
    3. Defaults definidos nesta classe
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicação ---
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Upload ---
    upload_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Tamanho máximo do arquivo em POST /extrair-nf (bytes, default: 10 MB)",
    )

    google_api_key: SecretStr | None = Field(
        default=None,
        description="Chave de API do Google AI Studio / Gemini",
    )
    gemini_model: str = Field(
        default="gemini-3.8-flash",
        description="Nome do modelo Gemini multimodal usado na extração",
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperatura do LLM (0.0 favorece extração determinística)",
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        gt=0.0,
        description="Timeout em segundos para cada chamada ao Gemini",
    )

    langsmith_tracing: bool = Field(
        default=False,
        description="Habilita o tracing das execuções LangChain no LangSmith",
    )
    langsmith_api_key: SecretStr | None = Field(
        default=None,
        description="Chave de API do LangSmith",
    )
    langsmith_project: str = Field(
        default="extracao-nf-llm",
        description="Projeto do LangSmith onde os traces são agrupados",
    )
    langsmith_endpoint: str | None = Field(
        default=None,
        description="Endpoint do LangSmith (ex.: região EU). Use null para o padrão",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton de Settings.

    O @lru_cache garante que a mesma instância seja reutilizada em toda a aplicação,
    evitando re-ler o .env a cada chamada. Para testes, use Settings() diretamente
    ou limpe o cache com get_settings.cache_clear().
    """
    return Settings()
