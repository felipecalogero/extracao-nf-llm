"""Enums de domínio (tipo de documento e de inconsistência)."""

from enum import StrEnum


class TipoDocumento(StrEnum):
    """Tipo do documento fiscal identificado na extração."""

    NFE = "NF-e"
    NFSE = "NFS-e"
    NFCE = "NFC-e"
    OUTRO = "outro"


class TipoInconsistencia(StrEnum):
    """Tipo de inconsistência detectada após a extração.

    Inconsistência não interrompe o processamento: o JSON continua válido,
    com o problema sinalizado nesta lista. Campo não encontrado usa ``null``,
    não uma inconsistência.
    """

    SOMA_PRODUTOS_DIVERGE_TOTAL = "soma_produtos_diverge_total"
    CAMPO_AUSENTE = "campo_ausente"
    FORMATO_INVALIDO = "formato_invalido"
