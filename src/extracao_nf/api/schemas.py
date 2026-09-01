"""Schemas de request/response da camada HTTP."""

from pydantic import BaseModel, Field


class ExtracaoStubResponse(BaseModel):
    """Resposta temporária do POST /extrair-nf enquanto o LLM não está integrado."""

    nome_arquivo: str = Field(description="Nome original do arquivo enviado")
    tamanho_bytes: int = Field(description="Tamanho do arquivo em bytes")
    content_type: str = Field(description="Tipo MIME validado do arquivo")
    mensagem: str = Field(
        default="Arquivo recebido com sucesso. Extração será implementada nas próximas etapas.",
        description="Mensagem informativa sobre o estado do processamento",
    )
