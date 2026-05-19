import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class HealthCheckResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Estado geral da API.")
    database = serializers.CharField(help_text="Estado da conexão com o banco de dados.")
    version = serializers.CharField(help_text="Versão da API.")


class ErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Estado geral da API.")
    database = serializers.CharField(help_text="Estado da conexão com o banco de dados.")
    version = serializers.CharField(help_text="Versão da API.")
    error = serializers.CharField(help_text="Mensagem de erro.", required=False)
