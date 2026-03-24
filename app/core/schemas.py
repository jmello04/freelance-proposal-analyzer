from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, field_validator


class NivelFreelancer(str, Enum):
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"


class Complexidade(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    MUITO_ALTA = "muito_alta"


TituloStr = Annotated[str, Field(min_length=5, max_length=200)]
DescricaoStr = Annotated[str, Field(min_length=20)]
ValorHoraFloat = Annotated[float, Field(gt=0, le=10_000)]


class EntradaProposta(BaseModel):
    titulo: TituloStr = Field(..., description="Título do projeto")
    descricao: DescricaoStr = Field(..., description="Descrição completa do que o cliente quer")
    prazo_cliente: str = Field(..., min_length=2, max_length=100, description="Prazo informado pelo cliente")
    tecnologias: List[str] = Field(..., description="Tecnologias mencionadas pelo cliente")
    nivel_freelancer: NivelFreelancer = Field(..., description="Nível de experiência: junior, pleno ou senior")
    valor_hora: ValorHoraFloat = Field(..., description="Valor hora pretendido em BRL")

    @field_validator("tecnologias")
    @classmethod
    def validar_tecnologias(cls, v: List[str]) -> List[str]:
        limpo = [t.strip() for t in v if t.strip()]
        if not limpo:
            raise ValueError("Informe ao menos uma tecnologia.")
        return limpo

    model_config = {
        "json_schema_extra": {
            "example": {
                "titulo": "Plataforma de E-commerce Completa",
                "descricao": (
                    "Preciso de uma loja virtual com carrinho de compras, checkout via Pix e cartão "
                    "de crédito (Stripe), painel administrativo para gestão de produtos e pedidos, "
                    "integração com Correios para cálculo de frete e emissão de nota fiscal eletrônica."
                ),
                "prazo_cliente": "3 meses",
                "tecnologias": ["Python", "Django", "React", "PostgreSQL", "Redis"],
                "nivel_freelancer": "pleno",
                "valor_hora": 85.0,
            }
        }
    }


class HorasEstimadas(BaseModel):
    min: int = Field(..., ge=1, description="Estimativa otimista em horas")
    max: int = Field(..., ge=1, description="Estimativa realista em horas")


class PrecoSugerido(BaseModel):
    min: float = Field(..., ge=0, description="Valor mínimo sugerido")
    max: float = Field(..., ge=0, description="Valor máximo sugerido")
    currency: str = Field(default="BRL")


class ResultadoAnalise(BaseModel):
    scope_summary: str = Field(..., description="Resumo claro do que foi pedido")
    estimated_hours: HorasEstimadas
    suggested_price: PrecoSugerido
    complexity: Complexidade
    risks: List[str] = Field(..., description="Riscos identificados no projeto")
    red_flags: List[str] = Field(..., description="Pontos de atenção críticos")
    questions_to_ask: List[str] = Field(..., description="Perguntas a fazer ao cliente")
    recommendation: str = Field(..., description="Recomendação final: aceitar, negociar ou recusar")


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


class RespostaErro(BaseModel):
    detail: str
    codigo: Optional[str] = None
