DC_EXEC = docker compose exec backend

.PHONY: install test test-cov show-cov lint format migrate makemigrations run shell check schema-validate ci help

help:
	@echo "Targets disponíveis:"
	@echo "  install          Instala dependências no container"
	@echo "  lint             Verifica ruff check + ruff format (sem alterar)"
	@echo "  format           Corrige com ruff --fix e formata com ruff format"
	@echo "  test             Roda pytest -v com coverage"
	@echo "  test-cov         Gera relatório HTML de coverage"
	@echo "  show-cov         Abre o relatório de coverage no navegador"
	@echo "  migrate          Aplica migrations pendentes"
	@echo "  makemigrations   Gera migrations para mudanças nos models"
	@echo "  run              Sobe o servidor de desenvolvimento"
	@echo "  shell            Abre o Django shell interativo"
	@echo "  check            Roda python manage.py check"
	@echo "  schema-validate  Valida schema OpenAPI (CI gate)"
	@echo "  ci               Roda lint + test + schema-validate (gate de PR)"

install:
	$(DC_EXEC) pip install -r requirements.txt

lint:
	$(DC_EXEC) ruff check .
	$(DC_EXEC) ruff format --check .

format:
	$(DC_EXEC) ruff check . --fix
	$(DC_EXEC) ruff format .

test:
	$(DC_EXEC) pytest -v

test-cov:
	$(DC_EXEC) pytest --cov=. --cov-report=html

show-cov:
	@python3 -c "import webbrowser, os; webbrowser.open('file://' + os.path.realpath('htmlcov/index.html'))" || python -c "import webbrowser, os; webbrowser.open('file://' + os.path.realpath('htmlcov/index.html'))"

migrate:
	$(DC_EXEC) python manage.py migrate

makemigrations:
	$(DC_EXEC) python manage.py makemigrations

run:
	docker compose up -d

shell:
	$(DC_EXEC) python manage.py shell

check:
	$(DC_EXEC) python manage.py check

schema-validate:
	$(DC_EXEC) python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml

ci: lint test schema-validate