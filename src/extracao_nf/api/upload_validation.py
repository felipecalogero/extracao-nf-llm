"""Validação de arquivos enviados via upload antes de chamar o LLM."""

from fastapi import HTTPException

TIPOS_MIME_PERMITIDOS = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
)


def _conteudo_corresponde_ao_tipo(conteudo: bytes, content_type: str) -> bool:
    """Verifica assinatura básica (magic bytes) do arquivo."""
    if content_type == "application/pdf":
        return conteudo.startswith(b"%PDF")
    if content_type == "image/png":
        return conteudo.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return conteudo.startswith(b"\xff\xd8\xff")
    return False


def validar_arquivo_upload(
    *,
    conteudo: bytes,
    content_type: str | None,
    tamanho_maximo_bytes: int,
) -> str:
    """Valida tipo, tamanho e integridade básica do arquivo.

    Returns:
        O content_type validado.

    Raises:
        HTTPException: 415 para tipo não suportado; 400 para vazio, grande ou corrompido.
    """
    if content_type not in TIPOS_MIME_PERMITIDOS:
        tipos = ", ".join(sorted(TIPOS_MIME_PERMITIDOS))
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de arquivo não suportado. Envie um dos tipos: {tipos}.",
        )

    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    if len(conteudo) > tamanho_maximo_bytes:
        raise HTTPException(
            status_code=400,
            detail=(f"Arquivo excede o tamanho máximo permitido ({tamanho_maximo_bytes} bytes)."),
        )

    if not _conteudo_corresponde_ao_tipo(conteudo, content_type):
        raise HTTPException(
            status_code=400,
            detail="Arquivo corrompido ou não corresponde ao tipo informado.",
        )

    return content_type
