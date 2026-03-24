# Freelance Proposal Analyzer

[![CI](https://github.com/jmello04/freelance-proposal-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/jmello04/freelance-proposal-analyzer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> Ferramenta de análise técnica de propostas freelance — estime horas, precifique projetos com precisão e identifique riscos antes de fechar qualquer contrato.

---

## Visão Geral

O **Freelance Proposal Analyzer** é uma aplicação web completa que recebe a descrição de um projeto freelance e retorna, em segundos, uma análise técnica detalhada contendo:

| Campo | Descrição |
|---|---|
| `scope_summary` | Resumo técnico de todos os requisitos identificados |
| `estimated_hours` | Estimativa de horas — cenário otimista e realista |
| `suggested_price` | Precificação sugerida em BRL (valor_hora × horas) |
| `complexity` | Nível de complexidade: baixa, média, alta ou muito alta |
| `risks` | Riscos técnicos e operacionais específicos do projeto |
| `red_flags` | Pontos críticos que podem gerar conflito ou prejuízo |
| `questions_to_ask` | Perguntas estratégicas para fazer ao cliente |
| `recommendation` | ACEITAR, NEGOCIAR (condições) ou RECUSAR (motivo) |

---

## Arquitetura

```
freelance-proposal-analyzer/
├── .github/
│   └── workflows/
│       └── ci.yml                   # Pipeline de CI — testes + lint automáticos
├── app/
│   ├── main.py                      # FastAPI app, middlewares, lifespan
│   ├── api/
│   │   └── v1/ → routes/
│   │       └── analysis.py          # Endpoints REST
│   ├── repositories/
│   │   └── analysis_repository.py   # Repository Pattern — toda lógica de banco
│   ├── services/
│   │   └── analyzer_service.py      # Motor de análise técnica (lazy init)
│   ├── core/
│   │   ├── config.py                # Settings com pydantic-settings v2
│   │   ├── exceptions.py            # Exceções HTTP tipadas e reutilizáveis
│   │   ├── logging.py               # Configuração centralizada de logging
│   │   └── schemas.py               # Schemas Pydantic v2 (entrada/saída)
│   ├── infra/
│   │   └── database/
│   │       ├── connection.py        # Engine async + get_db dependency
│   │       └── models.py            # Modelos SQLAlchemy com índices
│   └── static/
│       └── index.html               # SPA com Tailwind CSS
├── tests/
│   ├── conftest.py                  # Fixtures com SQLite in-memory
│   └── test_analysis.py             # 22 testes cobrindo todos os endpoints
├── .editorconfig                    # Consistência de estilo entre editores
├── Makefile                         # Comandos de desenvolvimento
├── pyproject.toml                   # Configuração de ruff (linter/formatter)
├── docker-compose.yml               # API + PostgreSQL com healthcheck
└── Dockerfile                       # Build multi-estágio: dev e prod
```

### Decisões de Arquitetura

**Repository Pattern** — toda lógica de banco de dados fica em `AnaliseRepository`, mantendo as rotas limpas e testáveis. Rotas recebem dados, delegam ao repositório e retornam schemas.

**Lazy Initialization** — `AnalisadorDePropostas` é instanciado apenas na primeira requisição real, evitando falha de inicialização em ambientes sem API key (testes, CI).

**Paginação com Metadados** — `GET /analyses` retorna `PaginaResposta` com `total`, `total_paginas`, `pagina` e `limite` além dos itens, seguindo padrão de APIs REST profissionais.

**Tratamento de Erros por Tipo** — `AuthenticationError` → 401, `RateLimitError` → 503, `ValueError` → 422. Sem `except Exception` genérico nas rotas.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.12 + FastAPI |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Banco de Dados** | PostgreSQL 16 |
| **Análise** | Anthropic API |
| **Frontend** | HTML5 + Tailwind CSS (CDN) |
| **Containers** | Docker + Docker Compose |
| **Testes** | pytest + pytest-asyncio + SQLite in-memory |
| **Qualidade** | Ruff (linter + formatter) |

---

## Requisitos

- Docker e Docker Compose
- Chave de API da Anthropic (`ANTHROPIC_API_KEY`)

---

## Instalação e Execução

### Com Docker Compose (recomendado)

```bash
# 1. Clonar o repositório
git clone https://github.com/jmello04/freelance-proposal-analyzer.git
cd freelance-proposal-analyzer

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e insira sua ANTHROPIC_API_KEY

# 3. Subir todos os serviços
docker-compose up --build
```

Acesse em:
- **Interface Web:** http://localhost:8000
- **Documentação Interativa:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Com Makefile (desenvolvimento local)

```bash
# Instalar dependências
make install

# Subir apenas o banco de dados
docker-compose up db -d

# Iniciar servidor com hot-reload
make run
```

Todos os comandos disponíveis:

```
make install      Instalar dependências do projeto
make run          Executar servidor de desenvolvimento
make test         Executar suite de testes
make test-cov     Executar testes com cobertura
make docker-up    Subir aplicação com Docker Compose
make docker-down  Parar e remover containers
make lint         Verificar qualidade do código
make format       Formatar código automaticamente
make clean        Remover arquivos temporários
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Chave de acesso à API **(obrigatória)** |
| `DATABASE_URL` | `postgresql+asyncpg://...` | URL de conexão com o banco |
| `ANALYSIS_MODEL` | `claude-sonnet-4-6` | Modelo para análise técnica |
| `ANALYSIS_MAX_TOKENS` | `2048` | Limite de tokens por análise |
| `LOG_LEVEL` | `INFO` | Nível de logging (`DEBUG`, `INFO`, `WARNING`) |

---

## Endpoints da API

### `POST /analyze` — Analisar proposta

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "Plataforma de E-commerce Completa",
    "descricao": "Preciso de uma loja virtual com carrinho de compras, checkout com Pix e cartão via Stripe, painel administrativo para gestão de produtos e pedidos, integração com Correios para frete e emissão de nota fiscal eletrônica.",
    "prazo_cliente": "3 meses",
    "tecnologias": ["Python", "Django", "React", "PostgreSQL"],
    "nivel_freelancer": "pleno",
    "valor_hora": 85.0
  }'
```

### `GET /analyses` — Listar com paginação e filtros

```bash
# Paginação
GET /analyses?pagina=1&limite=10

# Filtrar por complexidade
GET /analyses?complexidade=alta

# Filtrar por período
GET /analyses?data_inicio=2025-01-01T00:00:00&data_fim=2025-12-31T23:59:59
```

**Resposta:**
```json
{
  "total": 42,
  "pagina": 1,
  "limite": 10,
  "total_paginas": 5,
  "itens": [...]
}
```

### `GET /analyses/{id}` — Buscar por ID

```bash
GET /analyses/7
```

### `GET /stats` — Estatísticas gerais

```bash
GET /stats
```

```json
{
  "total_analises": 42,
  "preco_medio": { "min": 8500.0, "max": 14200.0, "currency": "BRL" },
  "horas_medias": { "min": 95.0, "max": 158.0 },
  "por_complexidade": { "alta": 18, "media": 14, "muito_alta": 7, "baixa": 3 }
}
```

### `GET /health` — Health check

```bash
GET /health
# → { "status": "ok", "versao": "1.0.0", "app": "Freelance Proposal Analyzer" }
```

---

## Exemplos Reais de Análise

### Exemplo 1 — App de Delivery "Igual ao iFood"

**Proposta do cliente:**
> "Preciso de um aplicativo de delivery idêntico ao iFood para minha cidade. Quero em 1 mês com orçamento de R$3.000."

**Análise esperada:**
```json
{
  "complexity": "muito_alta",
  "estimated_hours": { "min": 400, "max": 700 },
  "suggested_price": { "min": 36000, "max": 63000, "currency": "BRL" },
  "red_flags": [
    "Prazo de 1 mês para sistema desta magnitude é inviável — mínimo realista: 12 meses",
    "Orçamento de R$3.000 representa menos de 10% do valor mínimo estimado",
    "'Idêntico ao iFood' implica anos de desenvolvimento e equipes multidisciplinares"
  ],
  "recommendation": "RECUSAR — desalinhamento total entre expectativa e realidade. Prazo 10x menor que o necessário, orçamento 12x abaixo do mínimo."
}
```

---

### Exemplo 2 — Landing Page Corporativa

**Proposta do cliente:**
> "Quero uma landing page moderna para minha consultoria: seção hero, sobre nós, 4 serviços em cards, depoimentos, formulário de contato funcional e Google Analytics. Prazo: 2 semanas."

**Análise esperada:**
```json
{
  "complexity": "baixa",
  "estimated_hours": { "min": 16, "max": 28 },
  "suggested_price": { "min": 1360, "max": 2380, "currency": "BRL" },
  "risks": ["'Moderna' é subjetivo — validar referências visuais antes de iniciar"],
  "questions_to_ask": [
    "Você tem identidade visual (logo, cores, tipografia) definida?",
    "O conteúdo (textos e imagens) já está pronto?",
    "Vai precisar de painel para editar o conteúdo depois (CMS)?"
  ],
  "recommendation": "ACEITAR — escopo bem definido, prazo adequado e complexidade baixa."
}
```

---

### Exemplo 3 — Sistema para Clínica Médica

**Proposta do cliente:**
> "Sistema web para clínica: agendamento com calendário, prontuário eletrônico, notificações por WhatsApp, controle financeiro, relatórios e login com perfis de acesso. Prazo: 2 meses."

**Análise esperada:**
```json
{
  "complexity": "alta",
  "estimated_hours": { "min": 200, "max": 320 },
  "suggested_price": { "min": 17000, "max": 27200, "currency": "BRL" },
  "red_flags": [
    "Prazo de 2 meses é inviável para o escopo completo descrito",
    "WhatsApp pode exigir serviços pagos de terceiros (Z-API, Twilio)"
  ],
  "recommendation": "NEGOCIAR — projeto viável e bem remunerado, mas prazo deve ser estendido para 4 meses. Propor entrega em 2 fases."
}
```

---

## Testes

```bash
# Executar todos os testes
make test

# Com relatório de cobertura
make test-cov
```

A suite possui **22 testes** cobrindo:
- Sucesso e persistência no banco
- Todas as validações de entrada (Pydantic)
- Paginação — metadados, isolamento de páginas, offsets
- Filtros por complexidade
- Estatísticas com e sem dados
- Busca por ID — sucesso e not found
- Health check

Os testes utilizam **SQLite in-memory** e mocks do serviço externo, garantindo isolamento total e execução rápida sem dependências externas.

---

## Qualidade de Código

```bash
# Verificar estilo (CI roda automaticamente)
make lint

# Formatar automaticamente
make format
```

Configuração no `pyproject.toml`:
- `ruff` com regras: E, F, I (isort), N (naming), UP (modernização), B (bugbear), C4, RET, SIM

---

## CI/CD

O pipeline roda automaticamente a cada push e pull request para `main`:

1. **Testes** — executa a suite completa com Python 3.12
2. **Lint** — verifica qualidade e estilo com Ruff

Status atual: [![CI](https://github.com/jmello04/freelance-proposal-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/jmello04/freelance-proposal-analyzer/actions/workflows/ci.yml)

---

## Licença

MIT License — use, modifique e distribua livremente.
