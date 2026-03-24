from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnaliseNaoEncontradaError,
    ChaveApiInvalidaError,
    ServicoIndisponivelError,
)
from app.core.schemas import (
    Complexidade,
    EntradaProposta,
    HorasEstimadas,
    ItemListaAnalise,
    PrecoSugerido,
    RespostaAnalise,
    ResultadoAnalise,
)
from app.infra.database.connection import get_db
from app.infra.database.models import Analise
from app.services.analyzer_service import obter_analisador

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Análises"])


def _modelo_para_schema(analise: Analise) -> RespostaAnalise:
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
        "riscos, pontos de atenção, perguntas ao cliente e recomendação final."
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
    registro = Analise(
        titulo=entrada.titulo,
        descricao=entrada.descricao,
        prazo_cliente=entrada.prazo_cliente,
        tecnologias=entrada.tecnologias,
        nivel_freelancer=entrada.nivel_freelancer.value,
        valor_hora=entrada.valor_hora,
    )
    db.add(registro)
    await db.flush()

    try:
        analisador = obter_analisador()
        resultado = await analisador.analisar(entrada)
    except anthropic.AuthenticationError:
        await db.rollback()
        raise ChaveApiInvalidaError()
    except anthropic.RateLimitError:
        await db.rollback()
        raise ServicoIndisponivelError("limite de requisições atingido. Tente novamente em instantes.")
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        await db.rollback()
        logger.error("Erro de comunicação com serviço externo: %s", exc)
        raise ServicoIndisponivelError("falha de comunicação com serviço externo.")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Erro inesperado durante análise: %s", exc, exc_info=True)
        raise ServicoIndisponivelError("erro interno inesperado.")

    registro.scope_summary = resultado.scope_summary
    registro.horas_min = resultado.estimated_hours.min
    registro.horas_max = resultado.estimated_hours.max
    registro.preco_min = resultado.suggested_price.min
    registro.preco_max = resultado.suggested_price.max
    registro.complexidade = resultado.complexity.value
    registro.risks = resultado.risks
    registro.red_flags = resultado.red_flags
    registro.questions_to_ask = resultado.questions_to_ask
    registro.recommendation = resultado.recommendation

    await db.commit()
    await db.refresh(registro)

    logger.info("Análise %d salva: '%s'", registro.id, registro.titulo)
    return _modelo_para_schema(registro)


@router.get(
    "/analyses",
    response_model=List[ItemListaAnalise],
    summary="Listar análises anteriores",
    description="Retorna histórico paginado de análises com filtros por complexidade e período.",
    responses={
        200: {"description": "Lista de análises retornada com sucesso"},
    },
)
async def listar_analises(
    complexidade: Optional[Complexidade] = Query(None, description="Filtrar por nível de complexidade"),
    data_inicio: Optional[datetime] = Query(None, description="Data de início — ISO 8601 (ex: 2025-01-01T00:00:00)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim — ISO 8601 (ex: 2025-12-31T23:59:59)"),
    limite: int = Query(20, ge=1, le=100, description="Itens por página (máx. 100)"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    db: AsyncSession = Depends(get_db),
) -> List[ItemListaAnalise]:
    filtros = []

    if complexidade:
        filtros.append(Analise.complexidade == complexidade.value)
    if data_inicio:
        filtros.append(Analise.criado_em >= data_inicio)
    if data_fim:
        filtros.append(Analise.criado_em <= data_fim)

    offset = (pagina - 1) * limite
    query = (
        select(Analise)
        .where(and_(*filtros) if filtros else True)
        .order_by(Analise.criado_em.desc())
        .offset(offset)
        .limit(limite)
    )

    resultado = await db.execute(query)
    analises = resultado.scalars().all()

    return [
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


@router.get(
    "/analyses/{analise_id}",
    response_model=RespostaAnalise,
    summary="Buscar análise por ID",
    description="Retorna os detalhes completos de uma análise específica pelo seu identificador.",
    responses={
        200: {"description": "Análise encontrada"},
        404: {"description": "Análise não encontrada"},
    },
)
async def buscar_analise(
    analise_id: int,
    db: AsyncSession = Depends(get_db),
) -> RespostaAnalise:
    resultado = await db.execute(select(Analise).where(Analise.id == analise_id))
    analise = resultado.scalar_one_or_none()

    if not analise:
        raise AnaliseNaoEncontradaError(analise_id)

    return _modelo_para_schema(analise)
