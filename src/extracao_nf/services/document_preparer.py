"""Preparação de arquivos de NF para consumo multimodal pelo LangChain."""

import base64
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from extracao_nf.core.exceptions import ArquivoIlegivelError, ArquivoInvalidoError

TIPOS_MIME_SUPORTADOS = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
    }
)


@dataclass(frozen=True, slots=True)
class DocumentoPreparado:
    """Documento validado e codificado para mensagem multimodal do LangChain."""

    content_type: str
    tamanho_bytes: int
    data_uri: str


def _conteudo_corresponde_ao_tipo(conteudo: bytes, content_type: str) -> bool:
    """Verifica assinatura básica (magic bytes) do arquivo."""
    if content_type == "application/pdf":
        return conteudo.startswith(b"%PDF")
    if content_type == "image/png":
        return conteudo.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return conteudo.startswith(b"\xff\xd8\xff")
    return False


def _validar_imagem_legivel(conteudo: bytes) -> None:
    """Tenta abrir a imagem com Pillow para garantir que é legível."""
    try:
        with Image.open(BytesIO(conteudo)) as imagem:
            imagem.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ArquivoIlegivelError("Imagem ilegível ou corrompida.") from exc


def preparar_documento(*, conteudo: bytes, content_type: str) -> DocumentoPreparado:
    """Valida o arquivo e monta o payload data URI em base64 para o LLM.

    Args:
        conteudo: Bytes brutos do arquivo.
        content_type: Tipo MIME informado (application/pdf, image/png ou image/jpeg).

    Returns:
        DocumentoPreparado com data_uri no formato ``data:<mime>;base64,<...>``.

    Raises:
        ArquivoInvalidoError: arquivo vazio, tipo não suportado ou assinatura inválida.
        ArquivoIlegivelError: imagem com assinatura válida, mas ilegível pelo Pillow.
    """
    if len(conteudo) == 0:
        raise ArquivoInvalidoError("Arquivo vazio.")

    if content_type not in TIPOS_MIME_SUPORTADOS:
        tipos = ", ".join(sorted(TIPOS_MIME_SUPORTADOS))
        raise ArquivoInvalidoError(f"Tipo de arquivo não suportado: {content_type}. Use: {tipos}.")

    if not _conteudo_corresponde_ao_tipo(conteudo, content_type):
        raise ArquivoInvalidoError("Arquivo corrompido ou não corresponde ao tipo informado.")

    if content_type.startswith("image/"):
        _validar_imagem_legivel(conteudo)

    conteudo_base64 = base64.b64encode(conteudo).decode("ascii")
    data_uri = f"data:{content_type};base64,{conteudo_base64}"

    return DocumentoPreparado(
        content_type=content_type,
        tamanho_bytes=len(conteudo),
        data_uri=data_uri,
    )
