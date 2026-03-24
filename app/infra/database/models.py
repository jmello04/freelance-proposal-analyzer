from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.infra.database.connection import Base


class Analise(Base):
    __tablename__ = "analises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    titulo = Column(String(200), nullable=False, index=True)
    descricao = Column(Text, nullable=False)
    prazo_cliente = Column(String(100), nullable=False)
    tecnologias = Column(JSON, nullable=False)
    nivel_freelancer = Column(String(20), nullable=False, index=True)
    valor_hora = Column(Float, nullable=False)

    scope_summary = Column(Text, nullable=True)
    horas_min = Column(Integer, nullable=True)
    horas_max = Column(Integer, nullable=True)
    preco_min = Column(Float, nullable=True)
    preco_max = Column(Float, nullable=True)
    complexidade = Column(String(20), nullable=True, index=True)
    risks = Column(JSON, nullable=True)
    red_flags = Column(JSON, nullable=True)
    questions_to_ask = Column(JSON, nullable=True)
    recommendation = Column(Text, nullable=True)

    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Analise id={self.id} "
            f"titulo='{self.titulo[:30]}' "
            f"complexidade='{self.complexidade}'>"
        )
