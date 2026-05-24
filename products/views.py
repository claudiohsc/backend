import logging

from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsAdminRole

from .models import Category, DropCampaign, Product
from .serializers import (
    CategorySerializer,
    DropCampaignDetailSerializer,
    DropCampaignSerializer,
)

logger = logging.getLogger(__name__)


def inventory_summary(request):
    products = Product.objects.all()
    data = []
    for product in products:
        total_stock = product.variations.aggregate(total=Sum("stock_quantity"))["total"] or 0
        data.append({
            "name": product.name,
            "total_stock": total_stock,
        })
    return JsonResponse({"inventory": data})


# ─── Categories ───────────────────────────────────────────────────────────────


class CategoryListCreateView(APIView):
    """Listar categorias (público) e criar categoria (admin)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [AllowAny()]

    @extend_schema(
        tags=["Categories"],
        summary="Listar categorias",
        description="Lista paginada de categorias do catálogo. Endpoint público.",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        queryset = Category.objects.all().order_by("name")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CategorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Categories"],
        summary="Criar categoria",
        description=(
            "Cria uma nova categoria. Requer perfil ADMIN.\n\n"
            "O `slug` é gerado automaticamente a partir do `name` se não for enviado."
        ),
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Dados inválidos (ex: nome duplicado)."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
        },
    )
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category = serializer.save()
        logger.info(f"Categoria criada: {category.name} ({category.id})")
        return Response(
            CategorySerializer(category).data,
            status=status.HTTP_201_CREATED,
        )


class CategoryDetailView(APIView):
    """Detalhar (público); atualizar e remover (admin) uma categoria."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminRole()]

    def _get_object(self, pk):
        return get_object_or_404(Category, pk=pk)

    @extend_schema(
        tags=["Categories"],
        summary="Detalhe da categoria",
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Categoria não encontrada."),
        },
    )
    def get(self, request, pk):
        return Response(CategorySerializer(self._get_object(pk)).data)

    @extend_schema(
        tags=["Categories"],
        summary="Atualizar categoria (PUT)",
        description=(
            "Substitui os dados da categoria. Requer perfil ADMIN.\n\n"
            "Se `name` mudar e `slug` não for enviado, o slug é regenerado a partir do novo `name`."
        ),
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Dados inválidos."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(description="Categoria não encontrada."),
        },
    )
    def put(self, request, pk):
        category = self._get_object(pk)
        serializer = CategorySerializer(category, data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Categories"],
        summary="Remover categoria",
        description="Remove a categoria. Produtos relacionados ficam com `category=null`.",
        responses={
            204: OpenApiResponse(description="Categoria removida."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(description="Categoria não encontrada."),
        },
    )
    def delete(self, request, pk):
        category = self._get_object(pk)
        logger.info(f"Categoria removida: {category.name} ({category.id})")
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── DropCampaigns ────────────────────────────────────────────────────────────


class DropCampaignListCreateView(APIView):
    """Listar drops (público, com filtro ?active=true) e criar (admin)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminRole()]
        return [AllowAny()]

    @extend_schema(
        tags=["Drops"],
        summary="Listar drops",
        description=(
            "Lista paginada de campanhas de drop.\n\n"
            "Parâmetro opcional `?active=true` retorna apenas drops com "
            "`is_active=True` dentro do período `[launch_date, end_date]`."
        ),
        responses={200: DropCampaignSerializer(many=True)},
    )
    def get(self, request):
        queryset = DropCampaign.objects.all().order_by("-created_at")
        if request.query_params.get("active", "").lower() == "true":
            now = timezone.now()
            queryset = queryset.filter(is_active=True).filter(
                Q(launch_date__isnull=True) | Q(launch_date__lte=now)
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DropCampaignSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Drops"],
        summary="Criar drop",
        description=(
            "Cria uma nova campanha de drop. Requer perfil ADMIN.\n\n"
            "Aceita `multipart/form-data` com o campo `banner` (imagem)."
        ),
        request=DropCampaignSerializer,
        responses={
            201: DropCampaignSerializer,
            400: OpenApiResponse(description="Dados inválidos (ex: datas inconsistentes)."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
        },
    )
    def post(self, request):
        serializer = DropCampaignSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        drop = serializer.save()
        logger.info(f"Drop criado: {drop.name} ({drop.id})")
        return Response(
            DropCampaignSerializer(drop, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DropCampaignDetailView(APIView):
    """Detalhar drop com produtos nested (público); atualizar e remover (admin)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminRole()]

    def _get_object(self, pk):
        return get_object_or_404(DropCampaign, pk=pk)

    @extend_schema(
        tags=["Drops"],
        summary="Detalhe do drop com produtos",
        responses={
            200: DropCampaignDetailSerializer,
            404: OpenApiResponse(description="Drop não encontrado."),
        },
    )
    def get(self, request, pk):
        drop = self._get_object(pk)
        return Response(
            DropCampaignDetailSerializer(drop, context={"request": request}).data
        )

    @extend_schema(
        tags=["Drops"],
        summary="Atualizar drop (PUT)",
        description=(
            "Substitui os dados da campanha. Requer perfil ADMIN.\n\n"
            "Trocar o `banner` remove o arquivo antigo do storage."
        ),
        request=DropCampaignSerializer,
        responses={
            200: DropCampaignSerializer,
            400: OpenApiResponse(description="Dados inválidos."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(description="Drop não encontrado."),
        },
    )
    def put(self, request, pk):
        drop = self._get_object(pk)
        serializer = DropCampaignSerializer(drop, data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": "Dados inválidos.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Drops"],
        summary="Remover drop",
        description=(
            "Remove a campanha e o seu banner do storage.\n\n"
            "Produtos relacionados ficam com `drop=null` (`on_delete=SET_NULL`)."
        ),
        responses={
            204: OpenApiResponse(description="Drop removido."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(description="Drop não encontrado."),
        },
    )
    def delete(self, request, pk):
        drop = self._get_object(pk)
        logger.info(f"Drop removido: {drop.name} ({drop.id})")
        drop.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DropProductManageView(APIView):
    """Associar e desassociar um produto de um drop. Admin only."""

    permission_classes = [IsAdminRole]
    serializer_class = DropCampaignDetailSerializer

    def _get_drop(self, drop_id):
        return get_object_or_404(DropCampaign, pk=drop_id)

    def _get_product(self, product_id):
        return get_object_or_404(Product, pk=product_id)

    @extend_schema(
        tags=["Drops"],
        summary="Vincular produto ao drop",
        description=(
            "Associa um produto a este drop. Requer perfil ADMIN.\n\n"
            "Se o produto já estava em outro drop, é movido para este."
        ),
        request=None,
        responses={
            200: DropCampaignDetailSerializer,
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(description="Drop ou produto não encontrado."),
        },
    )
    def post(self, request, drop_id, product_id):
        drop = self._get_drop(drop_id)
        product = self._get_product(product_id)
        product.drop = drop
        product.save(update_fields=["drop", "updated_at"])
        logger.info(f"Produto {product.id} vinculado ao drop {drop.id}")
        return Response(
            DropCampaignDetailSerializer(drop, context={"request": request}).data
        )

    @extend_schema(
        tags=["Drops"],
        summary="Desvincular produto do drop",
        description=(
            "Remove a associação entre o produto e este drop (seta `drop=null`). "
            "Não apaga o produto."
        ),
        request=None,
        responses={
            204: OpenApiResponse(description="Produto desvinculado."),
            401: OpenApiResponse(description="Não autenticado."),
            403: OpenApiResponse(description="Não autorizado — requer perfil ADMIN."),
            404: OpenApiResponse(
                description="Drop ou produto não encontrado, ou produto não pertence a este drop."
            ),
        },
    )
    def delete(self, request, drop_id, product_id):
        drop = self._get_drop(drop_id)
        product = self._get_product(product_id)
        if product.drop_id != drop.id:
            return Response(
                {"error": "Produto não pertence a este drop."},
                status=status.HTTP_404_NOT_FOUND,
            )
        product.drop = None
        product.save(update_fields=["drop", "updated_at"])
        logger.info(f"Produto {product.id} desvinculado do drop {drop.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)
