# Shio API — Backend

API REST do e-commerce **Shio** em Django 5 + DRF, com autenticação JWT, login via Google OAuth, documentação OpenAPI (Swagger) e infraestrutura preparada para Cloudflare R2 (mídia) e SendGrid (e-mails transacionais).

## Visão Geral

- **Stack:** Python 3.12, Django 5.0, Django REST Framework, PostgreSQL, drf-spectacular
- **Arquitetura:** apps DDD com camadas `Model → Serializer → Service → View`
- **Apps atuais:** `authentication`, `shared`, `notifications`, `products`
- **Docs vivos:** [`docs/plano-arquitetura.md`](docs/plano-arquitetura.md) (roadmap, decisões, checklist)

## Pré-requisitos

- Docker + Docker Compose
- `make` (opcional, mas recomendado para os atalhos do `Makefile`)

## Setup inicial

```bash
# 1. Clonar
git clone https://github.com/Shio-Company/Backend.git && cd Backend

# 2. Variáveis de ambiente
cp .env.example .env
# Edite o .env e preencha DJANGO_SECRET_KEY, GOOGLE_CLIENT_ID, etc.

# 3. Gerar uma SECRET_KEY válida (opcional)
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 4. Permissão de execução no entrypoint
chmod +x entrypoint.sh

# 5. Subir os containers (DB + backend) — entrypoint já roda migrations e cria admin
docker compose up --build
```

A API fica disponível em `http://localhost:8000/`.

## Comandos do dia a dia (Makefile)

Todos os targets rodam dentro do container `backend`:

| Comando | O que faz |
|---------|-----------|
| `make help` | Lista todos os targets disponíveis |
| `make run` | Sobe os containers (`docker compose up`) |
| `make migrate` | Aplica migrations pendentes |
| `make makemigrations` | Gera novas migrations |
| `make shell` | Abre o `python manage.py shell` |
| `make check` | Roda `python manage.py check` |
| `make test` | Roda `pytest -v` com coverage |
| `make test-cov` | Gera relatório HTML de coverage |
| `make lint` | Verifica `ruff` + `black` (sem alterar) |
| `make format` | Formata com `black` e corrige com `ruff --fix` |
| `make schema-validate` | Valida o schema OpenAPI (`spectacular --validate --fail-on-warn`) |
| `make ci` | **Gate de PR:** `lint` + `test` + `schema-validate` |
| `make install` | Reinstala `requirements.txt` no container |

### Comandos equivalentes sem `make`

```bash
# Rodar manage.py dentro do container
docker compose exec backend python manage.py <comando>

# Exemplos:
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py shell
docker compose exec backend pytest -v
docker compose exec backend ruff check .
docker compose exec backend black --check .

# Instalar pacote novo no container (precisa de -u root)
docker compose exec -u root backend pip install <pacote>
```

## Documentação da API (Swagger / OpenAPI)

Com o servidor rodando:

- **Swagger UI:** http://localhost:8000/api/docs/
- **Redoc:** http://localhost:8000/api/redoc/
- **Schema bruto:** http://localhost:8000/api/schema/

> Regra do projeto: **100% dos endpoints obrigatoriamente decorados com `@extend_schema`**. O CI bloqueia PRs com warnings (`spectacular --validate --fail-on-warn`).

## Autenticação

A API suporta **dois fluxos de autenticação**, ambos retornando o mesmo par de tokens JWT:

### Google OAuth

```http
POST /api/auth/google/
{ "id_token": "<google-id-token>" }
```

### E-mail e senha

```http
POST /api/auth/register/
{ "email": "user@example.com", "password": "SenhaSegura123", "name": "Nome" }

POST /api/auth/login/
{ "email": "user@example.com", "password": "SenhaSegura123" }
```

Em qualquer fluxo a resposta é `{ "access", "refresh", "user", "is_new_user" }`.

Para endpoints protegidos: `Authorization: Bearer <access_token>`.

Renovar token: `POST /api/auth/token/refresh/`.

No Swagger UI, clicar em **Authorize** e colar `Bearer <access_token>`.

## Variáveis de ambiente importantes

Ver [`.env.example`](.env.example) para a lista completa. As principais:

| Variável | Descrição |
|----------|-----------|
| `SETTINGS_FILE_PATH` | `core.settings.dev` ou `core.settings.prod` |
| `DJANGO_SECRET_KEY` | Chave secreta do Django |
| `GOOGLE_CLIENT_ID` | Client ID do Google OAuth |
| `DB_NAME` / `DB_USERNAME` / `DB_PASSWORD` / `DB_HOSTNAME` / `DB_PORT` | Credenciais PostgreSQL |
| `ADMIN_NAME` / `ADMIN_PASS` / `ADMIN_EMAIL` | Superuser criado pelo `initadmin` |
| `ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` | CSV — usados em prod |
| `DEFAULT_FROM_EMAIL` / `SUPPORT_EMAIL` | Remetente padrão dos e-mails transacionais |
| `SENDGRID_API_KEY` | API key do SendGrid (apenas prod) |
| `R2_*` | Credenciais Cloudflare R2 (apenas prod) |

## E-mails transacionais

O app `notifications/` centraliza o envio via `NotificationService.send(template, recipient, context)`.

- **Dev:** `console.EmailBackend` (imprime no terminal)
- **Test:** `locmem.EmailBackend` (capturado em `mail.outbox`)
- **Prod:** `anymail.backends.sendgrid.EmailBackend`

Cada envio grava um `EmailLog` (auditoria + retry).

Testar localmente:

```bash
docker compose exec backend python manage.py send_test_email <destinatario@example.com>
docker compose exec backend python manage.py send_test_email <to> --template WELCOME
```

## Storage de mídia

- **Dev:** `FileSystemStorage` em `media/`
- **Prod:** `R2MediaStorage` (Cloudflare R2 via `django-storages[s3]`)

A classe está em `core/storages.py:R2MediaStorage` e é aplicada por field (ex: `ImageField(storage=R2MediaStorage())`).

## Testes

```bash
make test         # pytest -v com coverage
make test-cov     # gera htmlcov/index.html
```

`pytest-django` + `factory_boy` configurados. Factories ficam em cada app em `tests/factories.py`.

## Estrutura de Apps

```
backend/
├── core/                # settings, urls, wsgi, storages
│   ├── settings/        # base.py | dev.py | prod.py
│   └── storages.py      # R2MediaStorage
├── shared/              # TimestampedModel, permissions, exceptions, /api/health/
├── authentication/      # User custom + Google OAuth + JWT
├── notifications/       # EmailLog + NotificationService + templates de e-mail
├── products/            # Catalog atual (renomeado para `catalog/` na Fase 1)
├── docs/                # Documentação viva do projeto
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh        # migrate + initadmin + runserver
├── Makefile
├── pyproject.toml       # ruff + black + pytest
└── requirements.txt
```

