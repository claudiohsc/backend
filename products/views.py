import logging

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsAdminRole

from .models import Category, Product
from .serializers import CategorySerializer

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
