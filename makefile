DC_EXEC = docker compose exec backend

.PHONY: install test test-cov lint format migrate makemigrations run shell check schema-validate ci help

help:
	@echo "Targets disponíveis:"
	@echo "  install          Instala dependências no container"
	@echo "  lint             Verifica ruff + black (sem alterar)"
	@echo "  format           Formata com black e corrige com ruff --fix"
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
	$(DC_EXEC) black --check .

format:
	$(DC_EXEC) black .
	$(DC_EXEC) ruff check . --fix

migrate:
	$(DC_EXEC) python manage.py migrate

makemigrations:
	$(DC_EXEC) python manage.py makemigrations

run:
	docker compose up

shell:
	$(DC_EXEC) python manage.py shell

check:
	$(DC_EXEC) python manage.py check

schema-validate:
	$(DC_EXEC) python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml

ci: lint test schema-validate