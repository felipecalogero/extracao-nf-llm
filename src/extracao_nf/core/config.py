"""Configurações da aplicação (lê variáveis de ambiente)."""

from functools import lru_cache
from typing import Literal

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton de Settings.

    O @lru_cache garante que a mesma instância seja reutilizada em toda a aplicação,
    evitando re-ler o .env a cada chamada. Para testes, use Settings() diretamente
    ou limpe o cache com get_settings.cache_clear().
    """
    return Settings()
