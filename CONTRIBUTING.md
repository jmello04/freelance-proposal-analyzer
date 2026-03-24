# Guia de Contribuição

Obrigado pelo interesse em contribuir com o **Freelance Proposal Analyzer**!
Este documento descreve o processo para contribuir com o projeto de forma organizada.

---

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose
- Git configurado com nome e e-mail

---

## Configuração do Ambiente

```bash
# 1. Fork e clone do repositório
git clone https://github.com/SEU_USUARIO/freelance-proposal-analyzer.git
cd freelance-proposal-analyzer

# 2. Criar branch para a feature ou correção
git checkout -b feat/minha-feature
# ou
git checkout -b fix/meu-bugfix

# 3. Instalar dependências
make install

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações locais
```

---

## Fluxo de Desenvolvimento

### Executar a aplicação

```bash
# Subir banco de dados
docker-compose up db -d

# Iniciar servidor com hot-reload
make run
```

### Executar os testes

```bash
# Suite completa
make test

# Com relatório de cobertura
make test-cov
```

### Verificar qualidade do código

```bash
# Lint
make lint

# Formatar automaticamente
make format
```

---

## Padrão de Commits

Utilizamos **Conventional Commits**. Formato:

```
<tipo>(<escopo opcional>): <descrição curta>

<corpo opcional>
```

### Tipos aceitos

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Refatoração sem mudança de comportamento |
| `test` | Adição ou correção de testes |
| `docs` | Atualização de documentação |
| `chore` | Tarefas de manutenção (deps, config) |
| `perf` | Melhoria de performance |

### Exemplos

```bash
git commit -m "feat(api): adiciona filtro por nível de freelancer"
git commit -m "fix(repository): corrige contagem total em listar()"
git commit -m "test: adiciona testes para endpoint de estatísticas"
git commit -m "docs: atualiza exemplos de análise no README"
```

---

## Estrutura do Projeto

Antes de contribuir, familiarize-se com a arquitetura:

```
app/
├── api/routes/       → Endpoints FastAPI (finos — apenas orquestração)
├── repositories/     → Toda lógica de banco de dados (Repository Pattern)
├── services/         → Lógica de negócio e integrações externas
├── core/             → Schemas, config, exceptions, logging
└── infra/database/   → Models SQLAlchemy e conexão
```

**Regras de ouro:**
- Rotas **não** acessam banco diretamente — usam o repositório
- Repositórios **não** conhecem schemas Pydantic — trabalham com models
- Serviços **não** importam nada de `api/` ou `infra/`

---

## Pull Request

1. Garanta que todos os testes passam: `make test`
2. Garanta que o lint passa: `make lint`
3. Abra o PR com título seguindo Conventional Commits
4. Descreva o que mudou e por quê
5. Linke a issue relacionada (se houver)

O CI valida automaticamente testes e lint em todo PR.

---

## Reportar Bugs

Abra uma [Issue](https://github.com/jmello04/freelance-proposal-analyzer/issues) com:

- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs. observado
- Versão do Python e sistema operacional
