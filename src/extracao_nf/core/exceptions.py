"""Exceptions customizadas da aplicação.

Cada exception indica uma categoria de erro, permitindo tratamento diferenciado
na camada de API (ex.: 400 vs 422 vs 502).
"""


class ExtracaoNFError(Exception):
    """Exception base para todos os erros da aplicação."""

    pass


class ArquivoInvalidoError(ExtracaoNFError):
    """Arquivo ausente, vazio, tipo não suportado ou assinatura inválida."""

    pass


class ArquivoIlegivelError(ExtracaoNFError):
    """Arquivo reconhecido pelo tipo, mas ilegível (ex.: imagem corrompida)."""

    pass


class TransientError(ExtracaoNFError):
    # invariant: API mapeia para 502/504; retry controlado é permitido
    pass


class PermanentError(ExtracaoNFError):
    # invariant: não retentar automaticamente com a mesma entrada
    pass
