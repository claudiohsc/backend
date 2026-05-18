# Backend

## Visão Geral

Este repositório contém o backend Django da aplicação, com autenticação JWT e suporte a login via Google OAuth. A arquitetura segue a estrutura por apps Django, mantendo a separação entre `base`, `products` e `authentication`.

## Pré-requisitos

- Python 3.9+
- Docker e Docker Compose

## Dependências

As dependências do projeto estão em `requirements.txt`.

## Configuração do ambiente

1. Clone o repositório:

```bash
git clone https://github.com/Shio-Company/Backend.git && cd Backend
```

2. Copie o arquivo de exemplo de ambiente:

```bash
cp .env.example .env
```

3. Atualize os valores do `.env` conforme sua máquina.

4. Garanta permissões no `entrypoint.sh`:

```bash
chmod +x entrypoint.sh
```

## Executando com Docker

O modo recomendado é rodar a aplicação via Docker Compose.

```bash
docker compose up --build
```

O container já executa as migrações e cria o administrador automaticamente.

## Executando localmente

1. Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute migrações:

```bash
python manage.py migrate
```

4. Crie o superusuário com base nas variáveis de ambiente:

```bash
python manage.py initadmin
```

5. Inicie o servidor:

```bash
python manage.py runserver 0.0.0.0:8000
```

## Variáveis de ambiente importantes

- `SETTINGS_FILE_PATH`: caminho do settings, por exemplo `core.settings.dev`.
- `DJANGO_SECRET_KEY`: chave secreta do Django.
- `GOOGLE_CLIENT_ID`: client ID do OAuth do Google usado para validar `id_token`.
- `ADMIN_NAME`, `ADMIN_PASS`, `ADMIN_EMAIL`: credenciais para o superusuário inicial.

## Google Auth

A autenticação Google é feita em `POST /api/auth/google/`.

O frontend deve enviar um payload JSON com o campo `id_token` retornado pelo Google Sign-In.

Exemplo:

```json
{
  "id_token": "<google-id-token>"
}
```

A resposta inclui `access`, `refresh`, `user` e `is_new_user`.

## Testes

Execute os testes com:

```bash
python manage.py test
```

## Observações de arquitetura

- `authentication` contém o custom user model e a regra de negócio de login Google.
- `core/settings` é dividido em `base`, `dev` e `prod`.
- `base.py` define o modelo de usuário customizado `AUTH_USER_MODEL = "authentication.User"`.
- `entrypoint.sh` aplica migrações e cria o administrador antes de iniciar o serviço.
