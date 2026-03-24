from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")

from app.core.schemas import (
    Complexidade,
    HorasEstimadas,
    PrecoSugerido,
    ResultadoAnalise,
)
from app.infra.database.connection import Base, get_db
from app.main import app  # noqa: E402 (após setar env)

DATABASE_URL_TESTE = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(
        DATABASE_URL_TESTE,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        from app.infra.database import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine):
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def cliente_http(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def proposta_exemplo() -> dict:
    return {
        "titulo": "Sistema de Agendamento para Clínica Médica",
        "descricao": (
            "Preciso de um sistema web para gerenciar consultas de uma clínica médica. "
            "O sistema deve ter cadastro de pacientes, médicos e especialidades. "
            "Precisa de agenda visual com calendário, confirmação automática por WhatsApp "
            "e e-mail, prontuário eletrônico básico, relatórios mensais de atendimentos "
            "e painel administrativo com controle de acesso por perfil "
            "(admin, médico, recepcionista)."
        ),
        "prazo_cliente": "2 meses",
        "tecnologias": ["Python", "FastAPI", "React", "PostgreSQL"],
        "nivel_freelancer": "pleno",
        "valor_hora": 90.0,
    }


@pytest.fixture()
def resultado_mock() -> ResultadoAnalise:
    return ResultadoAnalise(
        scope_summary=(
            "Sistema web de gestão clínica com módulos de agendamento, cadastro de pacientes "
            "e médicos, prontuário eletrônico, notificações automáticas por WhatsApp e e-mail, "
            "relatórios mensais e painel administrativo com controle de acesso por perfil."
        ),
        estimated_hours=HorasEstimadas(min=160, max=260),
        suggested_price=PrecoSugerido(min=14400.0, max=23400.0, currency="BRL"),
        complexity=Complexidade.ALTA,
        risks=[
            "Prazo de 2 meses é insuficiente para o escopo descrito",
            "Integração com WhatsApp pode depender de serviços pagos (Z-API, Twilio)",
            "Prontuário eletrônico pode exigir conformidade com LGPD",
        ],
        red_flags=[
            "Prazo de 2 meses para um sistema desta complexidade é inviável",
            "Requisito de integração com WhatsApp pode dobrar o custo de operação",
        ],
        questions_to_ask=[
            "Quantos médicos e pacientes simultâneos são esperados?",
            "A integração com WhatsApp é obrigatória no MVP?",
            "Existe documentação das regras de negócio do prontuário?",
            "Há algum sistema atual sendo substituído?",
        ],
        recommendation=(
            "NEGOCIAR — o projeto é viável e bem remunerado, mas o prazo de 2 meses é inviável "
            "para o escopo completo. Proponha 4 meses e entrega em fases: agendamento e cadastros "
            "na fase 1; prontuário e relatórios na fase 2."
        ),
    )
