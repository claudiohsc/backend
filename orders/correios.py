import base64
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CORREIOS_TOKEN_CACHE_KEY = "correios_access_token"
CORREIOS_TOKEN_ENDPOINT = "https://api.correios.com.br/token/v1/autentica/cartaopostagem"
CORREIOS_TRACKING_ENDPOINT = "https://api.correios.com.br/srorastro/v1/objetos/{codigo_objeto}"
CORREIOS_PREPOSTAGEM_ENDPOINT = "https://api.correios.com.br/prepostagem/v1/prepostagens"
CORREIOS_PREPOSTAGEM_DETAILS_ENDPOINT = "https://api.correios.com.br/prepostagem/v1/prepostagens/{id}"


class CorreiosAuthenticationError(Exception):
    pass


class CorreiosTrackingUnavailableError(Exception):
    pass


class CorreiosPrePostagemError(Exception):
    pass


def build_basic_auth_header(username: str, password: str) -> str:
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"


def calculate_token_ttl_in_seconds(expires_at_iso: str) -> int:
    expires_at = datetime.fromisoformat(expires_at_iso)
    now = datetime.now(tz=expires_at.tzinfo)
    remaining_seconds = int((expires_at - now).total_seconds())
    return max(remaining_seconds - 60, 0)


def request_new_correios_access_token() -> str:
    username = settings.CORREIOS_USERNAME
    password = settings.CORREIOS_PASSWORD
    cartao_postagem = settings.CORREIOS_CARTAO_POSTAGEM

    headers = {
        "Authorization": build_basic_auth_header(username, password),
        "Content-Type": "application/json",
    }
    payload = {"numero": cartao_postagem}

    response = requests.post(CORREIOS_TOKEN_ENDPOINT, json=payload, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    token = data.get("token")
    expires_at = data.get("expiraEm")

    if not token or not expires_at:
        raise CorreiosAuthenticationError("Resposta de autenticação dos Correios inválida.")

    ttl = calculate_token_ttl_in_seconds(expires_at)
    if ttl > 0:
        cache.set(CORREIOS_TOKEN_CACHE_KEY, token, timeout=ttl)

    return token


def get_valid_correios_access_token() -> str:
    cached_token = cache.get(CORREIOS_TOKEN_CACHE_KEY)
    if cached_token:
        return cached_token
    return request_new_correios_access_token()


def fetch_tracking_data_from_correios(tracking_code: str) -> dict:
    token = get_valid_correios_access_token()
    url = CORREIOS_TRACKING_ENDPOINT.format(codigo_objeto=tracking_code)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 401:
        cache.delete(CORREIOS_TOKEN_CACHE_KEY)
        token = request_new_correios_access_token()
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(url, headers=headers, timeout=10)

    response.raise_for_status()
    return response.json()


def extract_most_recent_event_description(events: list[dict]) -> str:
    if not events:
        return ""
    return events[0].get("descricao", "")


def format_single_tracking_event(raw_event: dict) -> dict:
    unit = raw_event.get("unidade", {})
    address = unit.get("endereco", {})
    city = address.get("cidade", "")
    state = address.get("uf", "")
    location = f"{city} - {state}" if city and state else city or state

    return {
        "data": raw_event.get("dtHrCriado"),
        "descricao": raw_event.get("descricao", ""),
        "detalhe": raw_event.get("detalhe", ""),
        "local": location,
    }


def format_tracking_events_list(raw_events: list[dict]) -> list[dict]:
    return [format_single_tracking_event(event) for event in raw_events]


def build_tracking_response_from_correios_data(tracking_code: str, correios_data: dict) -> dict:
    objects = correios_data.get("objetos", [])
    if not objects:
        return build_empty_tracking_response(tracking_code)

    object_data = objects[0]
    raw_events = object_data.get("eventos", [])

    return {
        "tracking_code": tracking_code,
        "status_atual": extract_most_recent_event_description(raw_events),
        "previsao_entrega": object_data.get("dtPrevista"),
        "eventos": format_tracking_events_list(raw_events),
    }


def build_empty_tracking_response(tracking_code: str) -> dict:
    return {
        "tracking_code": tracking_code,
        "status_atual": "",
        "previsao_entrega": None,
        "eventos": [],
    }


def build_not_shipped_response() -> dict:
    return {
        "tracking_code": None,
        "status": "not_shipped",
        "eventos": [],
    }


def get_order_tracking_data(tracking_code: str | None) -> dict:
    if not tracking_code:
        return build_not_shipped_response()

    correios_data = fetch_tracking_data_from_correios(tracking_code)
    return build_tracking_response_from_correios_data(tracking_code, correios_data)


def build_remetente_data_from_settings() -> dict:
    return {
        "nome": settings.CORREIOS_REMETENTE_NOME,
        "email": settings.CORREIOS_REMETENTE_EMAIL,
        "cpfCnpj": settings.CORREIOS_REMETENTE_CPF_CNPJ,
        "endereco": {
            "cep": settings.CORREIOS_REMETENTE_CEP,
            "logradouro": settings.CORREIOS_REMETENTE_LOGRADOURO,
            "numero": settings.CORREIOS_REMETENTE_NUMERO,
            "complemento": settings.CORREIOS_REMETENTE_COMPLEMENTO,
            "bairro": settings.CORREIOS_REMETENTE_BAIRRO,
            "cidade": settings.CORREIOS_REMETENTE_CIDADE,
            "uf": settings.CORREIOS_REMETENTE_UF,
        },
    }


def build_destinatario_data_from_order(order) -> dict:
    user = order.user
    cpf_cnpj = ""
    if hasattr(user, "profile") and user.profile and user.profile.cpf:
        cpf_cnpj = user.profile.cpf

    return {
        "nome": user.name,
        "email": user.email,
        "cpfCnpj": cpf_cnpj,
        "endereco": {
            "cep": order.shipping_zip_code.replace("-", ""),
            "logradouro": order.shipping_street,
            "numero": order.shipping_number,
            "complemento": order.shipping_complement or "",
            "bairro": order.shipping_neighborhood,
            "cidade": order.shipping_city,
            "uf": order.shipping_state,
        },
    }


def build_prepostagem_payload_for_order(order) -> dict:
    return {
        "codigoServico": settings.CORREIOS_CODIGO_SERVICO,
        "codigoFormatoObjetoInformado": "1",
        "alturaInformada": "",
        "larguraInformada": "",
        "comprimentoInformado": "",
        "diametroInformado": "",
        "pesoInformado": settings.CORREIOS_PESO_PADRAO_GRAMAS,
        "remetente": build_remetente_data_from_settings(),
        "destinatario": build_destinatario_data_from_order(order),
    }


def extract_tracking_code_from_prepostagem_response(data: dict) -> str | None:
    objeto = data.get("objeto") or {}
    return objeto.get("codigoObjeto") or data.get("codigoObjeto")


def fetch_prepostagem_details_from_correios(prepostagem_id: str) -> dict:
    token = get_valid_correios_access_token()
    url = CORREIOS_PREPOSTAGEM_DETAILS_ENDPOINT.format(id=prepostagem_id)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 401:
        cache.delete(CORREIOS_TOKEN_CACHE_KEY)
        token = request_new_correios_access_token()
        headers["Authorization"] = f"Bearer {token}"
        response = requests.get(url, headers=headers, timeout=10)

    response.raise_for_status()
    return response.json()


def create_prepostagem_at_correios(order) -> dict:
    token = get_valid_correios_access_token()
    payload = build_prepostagem_payload_for_order(order)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.post(CORREIOS_PREPOSTAGEM_ENDPOINT, json=payload, headers=headers, timeout=15)

    if response.status_code == 401:
        cache.delete(CORREIOS_TOKEN_CACHE_KEY)
        token = request_new_correios_access_token()
        headers["Authorization"] = f"Bearer {token}"
        response = requests.post(CORREIOS_PREPOSTAGEM_ENDPOINT, json=payload, headers=headers, timeout=15)

    if not response.ok:
        try:
            error_detail = response.json()
        except Exception:
            error_detail = response.text
        raise CorreiosPrePostagemError(
            f"Falha ao criar pré-postagem: HTTP {response.status_code} - {error_detail}"
        )

    return response.json()


def dispatch_order_and_get_tracking_code(order) -> str:
    prepostagem_data = create_prepostagem_at_correios(order)

    tracking_code = extract_tracking_code_from_prepostagem_response(prepostagem_data)

    if not tracking_code:
        prepostagem_id = prepostagem_data.get("id")
        if prepostagem_id:
            details = fetch_prepostagem_details_from_correios(prepostagem_id)
            tracking_code = extract_tracking_code_from_prepostagem_response(details)

    if not tracking_code:
        raise CorreiosPrePostagemError(
            "Pré-postagem criada mas código de rastreio não encontrado na resposta dos Correios."
        )

    return tracking_code
