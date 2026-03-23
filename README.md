# Freelance Proposal Analyzer

> Ferramenta de análise técnica avançada para propostas freelance — estime horas, precifique projetos e identifique riscos antes de fechar qualquer contrato.

---

## Visão Geral

O **Freelance Proposal Analyzer** é uma aplicação web completa que recebe a descrição de um projeto freelance e retorna, em segundos, uma análise técnica detalhada contendo:

- Resumo objetivo do escopo identificado
- Estimativa de horas (mínimo e máximo)
- Sugestão de precificação em BRL
- Nível de complexidade do projeto
- Riscos técnicos e operacionais
- Pontos de atenção críticos (red flags)
- Perguntas estratégicas para fazer ao cliente
- Recomendação final sobre aceitar, negociar ou recusar

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Banco de Dados | PostgreSQL 16 + SQLAlchemy (async) |
| Frontend | HTML5 + Tailwind CSS (via CDN) |
| Análise Técnica | Anthropic API |
| Containerização | Docker + Docker Compose |
| Testes | pytest + pytest-asyncio |

---

## Estrutura do Projeto

```
freelance-proposal-analyzer/
├── app/
│   ├── main.py                      # Ponto de entrada da aplicação
│   ├── api/
│   │   └── routes/
│   │       └── analysis.py          # Endpoints REST
│   ├── services/
│   │   └── analyzer_service.py      # Motor de análise técnica
│   ├── infra/
│   │   └── database/
│   │       ├── connection.py        # Engine e sessão async
│   │       └── models.py            # Modelos SQLAlchemy
│   ├── core/
│   │   ├── config.py                # Configurações via variáveis de ambiente
│   │   └── schemas.py               # Schemas Pydantic (entrada/saída)
│   └── static/
│       └── index.html               # Interface web completa
├── tests/
│   ├── conftest.py                  # Fixtures e configuração do pytest
│   └── test_analysis.py             # Testes dos endpoints principais
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Requisitos

- Docker e Docker Compose instalados
- Chave de API da Anthropic (`ANTHROPIC_API_KEY`)

---

## Instalação e Execução

### 1. Clonar o repositório

```bash
git clone https://github.com/jmello04/freelance-proposal-analyzer.git
cd freelance-proposal-analyzer
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` e insira sua chave:

```env
ANTHROPIC_API_KEY=sua_chave_real_aqui
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/freelance_analyzer
```

### 3. Subir com Docker Compose

```bash
docker-compose up --build
```

A aplicação estará disponível em:

- **Interface Web:** http://localhost:8000
- **Documentação da API:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Execução Local (sem Docker)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Subir apenas o banco via Docker
docker-compose up db -d

# Executar a aplicação
uvicorn app.main:app --reload
```

---

## Endpoints da API

### `POST /analyze`
Analisa uma proposta freelance.

**Corpo da requisição:**
```json
{
  "titulo": "Plataforma de E-commerce Completa",
  "descricao": "Preciso de uma loja virtual com carrinho de compras, checkout com Pix e cartão via Stripe, painel administrativo para gestão de produtos e pedidos, integração com Correios para frete e emissão de nota fiscal.",
  "prazo_cliente": "3 meses",
  "tecnologias": ["Python", "Django", "React", "PostgreSQL"],
  "nivel_freelancer": "pleno",
  "valor_hora": 85.0
}
```

**Campos:**
| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `titulo` | string | ✓ | Título do projeto (5–200 chars) |
| `descricao` | string | ✓ | Descrição completa (mín. 20 chars) |
| `prazo_cliente` | string | ✓ | Prazo informado pelo cliente |
| `tecnologias` | array | ✓ | Lista de tecnologias mencionadas |
| `nivel_freelancer` | enum | ✓ | `junior`, `pleno` ou `senior` |
| `valor_hora` | float | ✓ | Valor hora em BRL (> 0) |

---

### `GET /analyses`
Lista análises anteriores com filtros opcionais.

**Parâmetros de query:**
| Parâmetro | Tipo | Descrição |
|---|---|---|
| `complexidade` | string | `baixa`, `media`, `alta`, `muito_alta` |
| `data_inicio` | datetime | Data de início (ISO 8601) |
| `data_fim` | datetime | Data de fim (ISO 8601) |
| `limite` | int | Itens por página (1–100, padrão: 20) |
| `pagina` | int | Número da página (padrão: 1) |

---

### `GET /analyses/{id}`
Retorna detalhes completos de uma análise específica.

---

### `GET /`
Serve a interface web.

---

## Exemplos de Análises Reais

### Exemplo 1 — App Mobile de Delivery

**Proposta do cliente:**
> "Preciso de um aplicativo de delivery igual ao iFood mas para a minha cidade. Quero em 1 mês e o orçamento é R$3.000."

**Resultado esperado:**
```json
{
  "complexity": "muito_alta",
  "estimated_hours": { "min": 400, "max": 700 },
  "suggested_price": { "min": 36000, "max": 63000, "currency": "BRL" },
  "red_flags": [
    "Prazo de 1 mês para um sistema desta magnitude é completamente inviável",
    "Orçamento de R$3.000 está 92% abaixo do mínimo estimado",
    "'Igual ao iFood' implica anos de desenvolvimento e equipes inteiras"
  ],
  "recommendation": "Recusar: há desalinhamento total entre expectativa e realidade técnica. O prazo é 10x menor que o necessário e o orçamento é 12x menor que o valor mínimo."
}
```

---

### Exemplo 2 — Landing Page Corporativa

**Proposta do cliente:**
> "Quero uma landing page moderna para minha empresa de consultoria. Precisa de seção hero, sobre nós, serviços (4 cards), depoimentos, formulário de contato funcional e integração com Google Analytics. Prazo: 2 semanas."

**Resultado esperado:**
```json
{
  "complexity": "baixa",
  "estimated_hours": { "min": 16, "max": 28 },
  "suggested_price": { "min": 1280, "max": 2240, "currency": "BRL" },
  "risks": [
    "Definição de 'moderna' é subjetiva — validar referências visuais antes de iniciar"
  ],
  "questions_to_ask": [
    "Você tem identidade visual (logo, paleta de cores, tipografia) definida?",
    "Há conteúdo (textos e imagens) pronto ou precisarei criar do zero?",
    "Será necessário painel para editar o conteúdo depois (CMS)?"
  ],
  "recommendation": "Aceitar: escopo bem definido, prazo adequado e complexidade baixa. Confirme apenas se há materiais prontos."
}
```

---

### Exemplo 3 — Sistema de Gestão para Clínica

**Proposta do cliente:**
> "Preciso de um sistema web para gerenciar uma clínica médica: agendamento com calendário interativo, prontuário eletrônico, notificações por WhatsApp, controle financeiro, relatórios e login com perfis diferentes. Prazo de 2 meses."

**Resultado esperado:**
```json
{
  "complexity": "alta",
  "estimated_hours": { "min": 200, "max": 320 },
  "suggested_price": { "min": 18000, "max": 28800, "currency": "BRL" },
  "risks": [
    "Prazo de 2 meses é insuficiente para o escopo completo descrito",
    "Integração com WhatsApp pode exigir serviços pagos de terceiros (Z-API, Twilio)",
    "Prontuário eletrônico pode envolver conformidade com LGPD e CFM"
  ],
  "recommendation": "Negociar: o projeto é viável e bem remunerado, mas o prazo precisa ser estendido para 4 meses. Proponha entrega em fases: agendamento e cadastros na fase 1, prontuário e financeiro na fase 2."
}
```

---

## Executar os Testes

```bash
# Instalar dependências de teste
pip install aiosqlite

# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ -v --tb=short
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Chave de acesso à API (obrigatória) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | URL de conexão com o banco |

---

## Licença

MIT License — use, modifique e distribua livremente.
