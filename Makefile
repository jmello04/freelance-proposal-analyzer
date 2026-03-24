PYTHON  := python3
PIP     := $(PYTHON) -m pip
UVICORN := uvicorn app.main:app

.PHONY: install run test test-cov docker-up docker-down docker-logs lint format clean help

install: ## Instalar dependências do projeto
	$(PIP) install -r requirements.txt

run: ## Executar servidor de desenvolvimento com hot-reload
	$(UVICORN) --reload --host 0.0.0.0 --port 8000

test: ## Executar suite de testes
	pytest tests/ -v --tb=short

test-cov: ## Executar testes com relatório de cobertura
	pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

docker-up: ## Subir aplicação completa com Docker Compose
	docker-compose up --build

docker-down: ## Parar e remover containers
	docker-compose down -v

docker-logs: ## Acompanhar logs da API em tempo real
	docker-compose logs -f api

lint: ## Verificar qualidade e estilo do código
	ruff check app/ tests/

format: ## Formatar código automaticamente
	ruff format app/ tests/

clean: ## Remover arquivos temporários e caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

help: ## Exibir lista de comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
