import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.infra.database.connection import Base, get_db
from app.core.schemas import (
    ResultadoAnalise,
    HorasEstimadas,
    PrecoSugerido,
    Complexidade,
)


DATABASE_URL_TESTE = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
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


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def cliente_http(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def proposta_exemplo():
    return {
        "titulo": "Sistema de Agendamento para Clínica Médica",
        "descricao": (
            "Preciso de um sistema web para gerenciar consultas de uma clínica médica. "
            "O sistema deve ter cadastro de pacientes, médicos e especialidades. "
            "Precisa de agenda visual (calendário), confirmação por WhatsApp e e-mail, "
            "prontuário eletrônico básico, relatórios de atendimentos mensais e "
            "painel administrativo para gestão. Login com diferentes níveis de acesso "
            "(admin, médico, recepcionista). Integração com planos de saúde é um plus."
        ),
        "prazo_cliente": "2 meses",
        "tecnologias": ["Python", "FastAPI", "React", "PostgreSQL"],
        "nivel_freelancer": "pleno",
        "valor_hora": 90.0,
    }


@pytest.fixture
def resultado_mock():
    return ResultadoAnalise(
        scope_summary=(
            "Sistema web de gestão clínica com módulos de agendamento, cadastro de pacientes e médicos, "
            "prontuário eletrônico, notificações por WhatsApp e e-mail, relatórios e painel administrativo "
            "com controle de acesso por perfil."
        ),
        estimated_hours=HorasEstimadas(min=160, max=260),
        suggested_price=PrecoSugerido(min=14400.0, max=23400.0, currency="BRL"),
        complexity=Complexidade.ALTA,
        risks=[
            "Prazo de 2 meses é insuficiente para o escopo descrito",
            "Integração com WhatsApp pode depender de serviços pagos (Twilio/Z-API)",
            "Integração com planos de saúde aumenta significativamente o escopo",
        ],
        red_flags=[
            "Prazo de 2 meses para um sistema desta complexidade é um red flag claro",
            "Requisito de integração com planos de saúde indefinido pode dobrar o escopo",
        ],
        questions_to_ask=[
            "Quantos médicos e pacientes são esperados no sistema?",
            "A integração com planos de saúde é obrigatória ou opcional?",
            "Já existe algum sistema sendo usado atualmente?",
            "Qual é o nível de disponibilidade necessário (24/7)?",
        ],
        recommendation=(
            "Negociar: o projeto é viável, mas o prazo de 2 meses é inviável para o escopo descrito. "
            "Recomendo propor 4 meses de prazo e definir a integração com planos de saúde como fase 2. "
            "Solicite documentação de todas as regras de negócio antes de fechar contrato."
        ),
    )
