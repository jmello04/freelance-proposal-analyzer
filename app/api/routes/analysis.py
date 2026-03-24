from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnaliseNaoEncontradaError,
    ChaveApiInvalidaError,
    ServicoIndisponivelError,
)
from app.core.schemas import (
    Complexidade,
    EntradaProposta,
    EstatisticasAnalise,
    HorasEstimadas,
    ItemListaAnalise,
    PaginaResposta,
    PrecoSugerido,
    RespostaAnalise,
    ResultadoAnalise,
)
from app.infra.database.connection import get_db
from app.infra.database.models import Analise
from app.repositories.analysis_repository import AnaliseRepository
from app.services.analyzer_service import obter_analisador

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Análises"])


def _para_schema(analise: Analise) -> RespostaAnalise:
    resultado = ResultadoAnalise(
        scope_summary=analise.scope_summary or "",
        estimated_hours=HorasEstimadas(
            min=analise.horas_min or 1,
            max=analise.horas_max or 1,
        ),
        suggested_price=PrecoSugerido(
            min=analise.preco_min or 0.0,
            max=analise.preco_max or 0.0,
            currency="BRL",
        ),
        complexity=Complexidade(analise.complexidade or "media"),
        risks=analise.risks or [],
        red_flags=analise.red_flags or [],
        questions_to_ask=analise.questions_to_ask or [],
        recommendation=analise.recommendation or "",
    )
    return RespostaAnalise(
        id=analise.id,
        titulo=analise.titulo,
        nivel_freelancer=analise.nivel_freelancer,
        valor_hora=analise.valor_hora,
        resultado=resultado,
        criado_em=analise.criado_em,
    )


@router.post(
    "/analyze",
    response_model=RespostaAnalise,
    status_code=status.HTTP_201_CREATED,
    summary="Analisar proposta freelance",
    description=(
        "Recebe os dados de uma proposta e retorna análise técnica completa: "
        "resumo de escopo, estimativa de horas, precificação em BRL, "
        "riscos identificados, pontos de atenção, perguntas estratégicas "
        "para o cliente e recomendação final."
    ),
    responses={
        201: {"description": "Análise criada com sucesso"},
        401: {"description": "Chave de API inválida ou ausente"},
        422: {"description": "Dados de entrada inválidos"},
        503: {"description": "Serviço temporariamente indisponível"},
    },
)
async def analisar_proposta(
    entrada: EntradaProposta,
    db: AsyncSession = Depends(get_db),
) -> RespostaAnalise:
    repo = AnaliseRepository(db)
    registro = await repo.criar_pendente(entrada)

    try:
        resultado = await obter_analisador().analisar(entrada)
    except anthropic.AuthenticationError:
        await db.rollback()
        raise ChaveApiInvalidaError()
    except anthropic.RateLimitError:
        await db.rollback()
        raise ServicoIndisponivelError("limite de requisições atingido. Tente novamente em instantes.")
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        await db.rollback()
        logger.error("Falha na comunicação com serviço externo: %s", exc)
        raise ServicoIndisponivelError("falha de comunicação com serviço externo.")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error("Erro inesperado durante análise: %s", exc, exc_info=True)
        raise ServicoIndisponivelError("erro interno inesperado.")

    analise = await repo.salvar_resultado(registro, resultado)
    return _para_schema(analise)


@router.get(
    "/analyses",
    response_model=PaginaResposta,
    summary="Listar análises anteriores",
    description=(
        "Retorna histórico paginado de análises com metadados de paginação. "
        "Suporta filtros por complexidade, data de início e data de fim."
    ),
)
async def listar_analises(
    complexidade: Optional[Complexidade] = Query(None, description="Filtrar por complexidade"),
    data_inicio: Optional[datetime] = Query(None, description="Data de início — ISO 8601"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim — ISO 8601"),
    limite: int = Query(20, ge=1, le=100, description="Itens por página"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    db: AsyncSession = Depends(get_db),
) -> PaginaResposta:
    repo = AnaliseRepository(db)
    offset = (pagina - 1) * limite
    analises, total = await repo.listar(
        complexidade=complexidade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite,
        offset=offset,
    )
    itens = [
        ItemListaAnalise(
            id=a.id,
            titulo=a.titulo,
            complexidade=a.complexidade or "media",
            preco_min=a.preco_min or 0.0,
            preco_max=a.preco_max or 0.0,
            horas_min=a.horas_min or 0,
            horas_max=a.horas_max or 0,
            nivel_freelancer=a.nivel_freelancer,
            criado_em=a.criado_em,
        )
        for a in analises
    ]
    return PaginaResposta.montar(itens=itens, total=total, pagina=pagina, limite=limite)


@router.get(
    "/analyses/{analise_id}",
    response_model=RespostaAnalise,
    summary="Buscar análise por ID",
    description="Retorna os detalhes completos de uma análise específica.",
    responses={
        200: {"description": "Análise encontrada"},
        404: {"description": "Análise não encontrada"},
    },
)
async def buscar_analise(
    analise_id: int,
    db: AsyncSession = Depends(get_db),
) -> RespostaAnalise:
    repo = AnaliseRepository(db)
    analise = await repo.buscar_por_id(analise_id)
    if not analise:
        raise AnaliseNaoEncontradaError(analise_id)
    return _para_schema(analise)


@router.get(
    "/stats",
    response_model=EstatisticasAnalise,
    tags=["Sistema"],
    summary="Estatísticas gerais das análises",
    description="Retorna métricas agregadas de todas as análises realizadas.",
)
async def estatisticas(
    db: AsyncSession = Depends(get_db),
) -> EstatisticasAnalise:
    repo = AnaliseRepository(db)
    dados = await repo.estatisticas()
    return EstatisticasAnalise(**dados)
