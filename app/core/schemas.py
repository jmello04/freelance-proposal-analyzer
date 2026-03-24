from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class NivelFreelancer(StrEnum):
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"


class Complexidade(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    MUITO_ALTA = "muito_alta"


TituloStr = Annotated[str, Field(min_length=5, max_length=200)]
DescricaoStr = Annotated[str, Field(min_length=20)]
ValorHoraFloat = Annotated[float, Field(gt=0, le=10_000)]


# ── Entrada ───────────────────────────────────────────────────

class EntradaProposta(BaseModel):
    titulo: TituloStr = Field(..., description="Título do projeto")
    descricao: DescricaoStr = Field(..., description="Descrição completa do que o cliente quer")
    prazo_cliente: str = Field(
        ..., min_length=2, max_length=100, description="Prazo informado pelo cliente"
    )
    tecnologias: list[str] = Field(..., description="Tecnologias mencionadas pelo cliente")
    nivel_freelancer: NivelFreelancer = Field(
        ..., description="Nível de experiência: junior, pleno ou senior"
    )
    valor_hora: ValorHoraFloat = Field(..., description="Valor hora pretendido em BRL")

    @field_validator("tecnologias")
    @classmethod
    def validar_tecnologias(cls, v: list[str]) -> list[str]:
        limpo = [t.strip() for t in v if t.strip()]
        if not limpo:
            raise ValueError("Informe ao menos uma tecnologia.")
        return limpo

    model_config = {
        "json_schema_extra": {
            "example": {
                "titulo": "Plataforma de E-commerce Completa",
                "descricao": (
                    "Preciso de uma loja virtual com carrinho de compras, checkout via Pix e "
                    "cartão de crédito (Stripe), painel administrativo para gestão de produtos "
                    "e pedidos, integração com Correios para frete e emissão de nota fiscal."
                ),
                "prazo_cliente": "3 meses",
                "tecnologias": ["Python", "Django", "React", "PostgreSQL", "Redis"],
                "nivel_freelancer": "pleno",
                "valor_hora": 85.0,
            }
        }
    }


# ── Resultado de Análise ──────────────────────────────────────

class HorasEstimadas(BaseModel):
    min: int = Field(..., ge=1, description="Estimativa otimista em horas")
    max: int = Field(..., ge=1, description="Estimativa realista em horas")


class PrecoSugerido(BaseModel):
    min: float = Field(..., ge=0, description="Valor mínimo sugerido")
    max: float = Field(..., ge=0, description="Valor máximo sugerido")
    currency: str = Field(default="BRL")


class ResultadoAnalise(BaseModel):
    scope_summary: str = Field(..., description="Resumo claro do escopo identificado")
    estimated_hours: HorasEstimadas
    suggested_price: PrecoSugerido
    complexity: Complexidade
    risks: list[str] = Field(..., description="Riscos identificados no projeto")
    red_flags: list[str] = Field(..., description="Pontos de atenção críticos")
    questions_to_ask: list[str] = Field(
        ..., description="Perguntas a fazer ao cliente antes de fechar"
    )
    recommendation: str = Field(..., description="Recomendação final: ACEITAR, NEGOCIAR ou RECUSAR")


# ── Respostas da API ──────────────────────────────────────────

class RespostaAnalise(BaseModel):
    id: int
    titulo: str
    nivel_freelancer: str
    valor_hora: float
    resultado: ResultadoAnalise
    criado_em: datetime

    model_config = {"from_attributes": True}


class ItemListaAnalise(BaseModel):
    id: int
    titulo: str
    complexidade: str
    preco_min: float
    preco_max: float
    horas_min: int
    horas_max: int
    nivel_freelancer: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class PaginaResposta(BaseModel):
    total: int = Field(..., description="Total de registros encontrados")
    pagina: int = Field(..., description="Página atual")
    limite: int = Field(..., description="Itens por página")
    total_paginas: int = Field(..., description="Total de páginas disponíveis")
    itens: list[ItemListaAnalise]

    @classmethod
    def montar(
        cls,
        itens: list[ItemListaAnalise],
        total: int,
        pagina: int,
        limite: int,
    ) -> PaginaResposta:
        total_paginas = math.ceil(total / limite) if total and limite else 0
        return cls(
            total=total, pagina=pagina, limite=limite, total_paginas=total_paginas, itens=itens
        )


# ── Estatísticas ──────────────────────────────────────────────

class PrecoMedioStats(BaseModel):
    min: float
    max: float
    currency: str = "BRL"


class HorasMediasStats(BaseModel):
    min: float
    max: float


class EstatisticasAnalise(BaseModel):
    total_analises: int
    preco_medio: PrecoMedioStats
    horas_medias: HorasMediasStats
    por_complexidade: dict[str, int]


# ── Erros ─────────────────────────────────────────────────────

class RespostaErro(BaseModel):
    detail: str
    codigo: str | None = None
