from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime

from app.core.schemas import (
    EntradaProposta,
    RespostaAnalise,
    ItemListaAnalise,
    ResultadoAnalise,
    HorasEstimadas,
    PrecoSugerido,
    Complexidade,
    FiltrosAnalise,
)
from app.infra.database.connection import get_db
from app.infra.database.models import Analise
from app.services.analyzer_service import analisador

router = APIRouter(tags=["Análises"])


def _modelo_para_schema(analise: Analise) -> RespostaAnalise:
    resultado = ResultadoAnalise(
        scope_summary=analise.scope_summary or "",
        estimated_hours=HorasEstimadas(
            min=analise.horas_min or 0,
            max=analise.horas_max or 0,
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
    description="Recebe os dados de uma proposta freelance e retorna análise técnica detalhada com estimativa de horas, precificação e identificação de riscos.",
)
async def analisar_proposta(
    entrada: EntradaProposta,
    db: AsyncSession = Depends(get_db),
) -> RespostaAnalise:
    novo_registro = Analise(
        titulo=entrada.titulo,
        descricao=entrada.descricao,
        prazo_cliente=entrada.prazo_cliente,
        tecnologias=entrada.tecnologias,
        nivel_freelancer=entrada.nivel_freelancer.value,
        valor_hora=entrada.valor_hora,
    )
    db.add(novo_registro)
    await db.flush()

    try:
        resultado = await analisador.analisar(entrada)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Falha no processamento da proposta: {str(exc)}",
        )

    novo_registro.scope_summary = resultado.scope_summary
    novo_registro.horas_min = resultado.estimated_hours.min
    novo_registro.horas_max = resultado.estimated_hours.max
    novo_registro.preco_min = resultado.suggested_price.min
    novo_registro.preco_max = resultado.suggested_price.max
    novo_registro.complexidade = resultado.complexity.value
    novo_registro.risks = resultado.risks
    novo_registro.red_flags = resultado.red_flags
    novo_registro.questions_to_ask = resultado.questions_to_ask
    novo_registro.recommendation = resultado.recommendation

    await db.commit()
    await db.refresh(novo_registro)

    return _modelo_para_schema(novo_registro)


@router.get(
    "/analyses",
    response_model=List[ItemListaAnalise],
    summary="Listar análises anteriores",
    description="Retorna histórico de análises com filtros opcionais por complexidade e período.",
)
async def listar_analises(
    complexidade: Optional[Complexidade] = Query(None, description="Filtrar por complexidade"),
    data_inicio: Optional[datetime] = Query(None, description="Data de início (ISO 8601)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (ISO 8601)"),
    limite: int = Query(20, ge=1, le=100, description="Itens por página"),
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
    description="Retorna os detalhes completos de uma análise específica.",
)
async def buscar_analise(
    analise_id: int,
    db: AsyncSession = Depends(get_db),
) -> RespostaAnalise:
    resultado = await db.execute(select(Analise).where(Analise.id == analise_id))
    analise = resultado.scalar_one_or_none()

    if not analise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise com ID {analise_id} não encontrada.",
        )

    return _modelo_para_schema(analise)
