import logging

from django.conf import settings
from django.db import connection
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ErrorResponseSerializer, HealthCheckResponseSerializer

logger = logging.getLogger(__name__)

_VERSION = settings.SPECTACULAR_SETTINGS.get("VERSION", "unknown")


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description=(
        "Verifica o estado da API e da conexão com o banco de dados.\n\n"
        "**Retorna 200** quando a API e o banco estão operacionais.\n"
        "**Retorna 503** quando a conexão com o banco falha."
    ),
    responses={
        200: OpenApiResponse(
            response=HealthCheckResponseSerializer,
            description="API e banco operacionais.",
            examples=[
                OpenApiExample(
                    name="Saudável",
                    value={"status": "ok", "database": "connected", "version": "1.0.0"},
                    response_only=True,
                    status_codes=["200"],
                )
            ],
        ),
        503: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Banco de dados inacessível.",
            examples=[
                OpenApiExample(
                    name="DB indisponível",
                    value={"status": "error", "database": "disconnected", "version": "1.0.0"},
                    response_only=True,
                    status_codes=["503"],
                )
            ],
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    payload = {"status": "ok", "database": "disconnected", "version": _VERSION}
    try:
        connection.ensure_connection()
        payload["database"] = "connected"
    except Exception:
        logger.error("Health check: falha na conexão com o banco de dados.")
        payload["status"] = "error"
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload, status=status.HTTP_200_OK)
