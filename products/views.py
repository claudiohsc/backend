import logging

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import InventorySummarySerializer
from .services import InventoryService

logger = logging.getLogger(__name__)


class InventorySummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Products"],
        summary="Resumo de inventário",
        description=(
            "Retorna um resumo agregado do inventário de produtos ativos.\n\n"
            "**Requer:** utilizador autenticado com `is_staff=True`."
        ),
        responses={
            200: OpenApiResponse(
                response=InventorySummarySerializer,
                description="Resumo calculado com sucesso.",
                examples=[
                    OpenApiExample(
                        name="Resumo",
                        value={"total_products": 42, "total_stock": 1280, "low_stock_count": 5},
                        response_only=True,
                        status_codes=["200"],
                    )
                ],
            ),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Acesso negado — requer is_staff."),
        },
    )
    def get(self, request):
        data = InventoryService.get_summary()
        serializer = InventorySummarySerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
