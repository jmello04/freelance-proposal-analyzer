from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class NivelFreelancer(str, Enum):
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"


class Complexidade(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    MUITO_ALTA = "muito_alta"


class EntradaProposta(BaseModel):
    titulo: str = Field(..., min_length=5, max_length=200, description="Título do projeto")
    descricao: str = Field(..., min_length=20, description="Descrição completa do projeto")
    prazo_cliente: str = Field(..., description="Prazo informado pelo cliente")
    tecnologias: List[str] = Field(..., min_length=1, description="Tecnologias mencionadas")
    nivel_freelancer: NivelFreelancer = Field(..., description="Nível de experiência do freelancer")
    valor_hora: float = Field(..., gt=0, description="Valor hora pretendido em BRL")

    @field_validator("tecnologias")
    @classmethod
    def validar_tecnologias(cls, v: List[str]) -> List[str]:
        return [t.strip() for t in v if t.strip()]

    model_config = {
        "json_schema_extra": {
            "example": {
                "titulo": "Plataforma de E-commerce Completa",
                "descricao": "Preciso de uma loja virtual com carrinho de compras, checkout com Pix e cartão de crédito via Stripe, painel administrativo para gestão de produtos e pedidos, integração com Correios para frete e emissão de nota fiscal.",
                "prazo_cliente": "3 meses",
                "tecnologias": ["Python", "Django", "React", "PostgreSQL", "Redis"],
                "nivel_freelancer": "pleno",
                "valor_hora": 85.0,
            }
        }
    }


class HorasEstimadas(BaseModel):
    min: int = Field(..., ge=1)
    max: int = Field(..., ge=1)


class PrecoSugerido(BaseModel):
    min: float = Field(..., ge=0)
    max: float = Field(..., ge=0)
    currency: str = Field(default="BRL")


class ResultadoAnalise(BaseModel):
    scope_summary: str
    estimated_hours: HorasEstimadas
    suggested_price: PrecoSugerido
    complexity: Complexidade
    risks: List[str]
    red_flags: List[str]
    questions_to_ask: List[str]
    recommendation: str


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


class FiltrosAnalise(BaseModel):
    complexidade: Optional[Complexidade] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    limite: int = Field(default=20, ge=1, le=100)
    pagina: int = Field(default=1, ge=1)
