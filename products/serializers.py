import logging

from django.core.validators import MinValueValidator
from rest_framework import serializers

from .models import Category, Product, ProductVariation

logger = logging.getLogger(__name__)


class InventorySummarySerializer(serializers.Serializer):
    total_products = serializers.IntegerField(help_text="Total de produtos ativos no catálogo.")
    total_stock = serializers.IntegerField(
        help_text="Soma total de unidades em estoque (todas as variações)."
    )
    low_stock_count = serializers.IntegerField(
        help_text="Produtos ativos com estoque total ≤ 5 unidades."
    )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
        read_only_fields = ["id"]


class ProductVariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariation
        fields = ["id", "size", "stock_quantity"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "size": {"help_text": "Tamanho da variação (ex: P, M, G, XL)."},
            "stock_quantity": {"help_text": "Quantidade disponível em estoque."},
        }


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variations = ProductVariationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "base_price",
            "is_active",
            "created_at",
            "variations",
        ]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "name": {"help_text": "Nome do produto."},
            "description": {"help_text": "Descrição detalhada do produto."},
            "base_price": {
                "help_text": "Preço base do produto (em BRL). Deve ser maior que zero.",
                "validators": [MinValueValidator(0.01)],
            },
            "is_active": {"help_text": "Indica se o produto está disponível para venda."},
        }
