from fastapi import HTTPException, status


class PropostaInvalidaError(HTTPException):
    def __init__(self, detalhe: str) -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detalhe)


class AnaliseNaoEncontradaError(HTTPException):
    def __init__(self, analise_id: int) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise com ID {analise_id} não encontrada.",
        )


class ServicoIndisponivelError(HTTPException):
    def __init__(self, detalhe: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço temporariamente indisponível: {detalhe}",
        )


class ChaveApiInvalidaError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou sem permissão. Verifique ANTHROPIC_API_KEY.",
        )
