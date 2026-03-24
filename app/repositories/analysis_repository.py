from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import Complexidade, EntradaProposta, ResultadoAnalise
from app.infra.database.models import Analise

logger = logging.getLogger(__name__)


class AnaliseRepository:
    """Encapsula todas as operações de banco de dados relacionadas a análises."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar_pendente(self, entrada: EntradaProposta) -> Analise:
        analise = Analise(
            titulo=entrada.titulo,
            descricao=entrada.descricao,
            prazo_cliente=entrada.prazo_cliente,
            tecnologias=entrada.tecnologias,
            nivel_freelancer=entrada.nivel_freelancer.value,
            valor_hora=entrada.valor_hora,
        )
        self._session.add(analise)
        await self._session.flush()
        logger.debug("Registro pendente criado: id=%d", analise.id)
        return analise

    async def salvar_resultado(
        self, analise: Analise, resultado: ResultadoAnalise
    ) -> Analise:
        analise.scope_summary = resultado.scope_summary
        analise.horas_min = resultado.estimated_hours.min
        analise.horas_max = resultado.estimated_hours.max
        analise.preco_min = resultado.suggested_price.min
        analise.preco_max = resultado.suggested_price.max
        analise.complexidade = resultado.complexity.value
        analise.risks = resultado.risks
        analise.red_flags = resultado.red_flags
        analise.questions_to_ask = resultado.questions_to_ask
        analise.recommendation = resultado.recommendation

        await self._session.commit()
        await self._session.refresh(analise)
        logger.info(
            "Análise %d persistida | complexidade=%s | preço=R$%.0f-R$%.0f",
            analise.id,
            analise.complexidade,
            analise.preco_min,
            analise.preco_max,
        )
        return analise

    async def buscar_por_id(self, analise_id: int) -> Optional[Analise]:
        result = await self._session.execute(
            select(Analise).where(Analise.id == analise_id)
        )
        return result.scalar_one_or_none()

    async def listar(
        self,
        complexidade: Optional[Complexidade] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limite: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Analise], int]:
        where = self._montar_where(complexidade, data_inicio, data_fim)

        total = await self._contar(where)
        analises = await self._buscar_pagina(where, limite, offset)
        return analises, total

    async def estatisticas(self) -> dict:
        agg = await self._session.execute(
            select(
                func.count(Analise.id).label("total"),
                func.avg(Analise.preco_min).label("preco_medio_min"),
                func.avg(Analise.preco_max).label("preco_medio_max"),
                func.avg(Analise.horas_min).label("horas_media_min"),
                func.avg(Analise.horas_max).label("horas_media_max"),
            )
        )
        row = agg.one()

        dist = await self._session.execute(
            select(Analise.complexidade, func.count(Analise.id).label("qtd"))
            .where(Analise.complexidade.isnot(None))
            .group_by(Analise.complexidade)
            .order_by(func.count(Analise.id).desc())
        )

        return {
            "total_analises": row.total or 0,
            "preco_medio": {
                "min": round(row.preco_medio_min or 0.0, 2),
                "max": round(row.preco_medio_max or 0.0, 2),
                "currency": "BRL",
            },
            "horas_medias": {
                "min": round(row.horas_media_min or 0.0, 1),
                "max": round(row.horas_media_max or 0.0, 1),
            },
            "por_complexidade": {r.complexidade: r.qtd for r in dist},
        }

    # ── helpers privados ──────────────────────────────────────

    def _montar_where(
        self,
        complexidade: Optional[Complexidade],
        data_inicio: Optional[datetime],
        data_fim: Optional[datetime],
    ):
        filtros = []
        if complexidade:
            filtros.append(Analise.complexidade == complexidade.value)
        if data_inicio:
            filtros.append(Analise.criado_em >= data_inicio)
        if data_fim:
            filtros.append(Analise.criado_em <= data_fim)
        return and_(*filtros) if filtros else True

    async def _contar(self, where) -> int:
        result = await self._session.execute(
            select(func.count(Analise.id)).where(where)
        )
        return result.scalar() or 0

    async def _buscar_pagina(self, where, limite: int, offset: int) -> List[Analise]:
        result = await self._session.execute(
            select(Analise)
            .where(where)
            .order_by(Analise.criado_em.desc())
            .offset(offset)
            .limit(limite)
        )
        return list(result.scalars().all())
