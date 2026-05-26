from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CustomerOrder
from products.models import ProductVariation

User = get_user_model()


class DashboardRecentOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrder
        fields = ["id", "customer_name", "total_amount", "status", "created_at"]

    def get_customer_name(self, obj):
        return getattr(obj.user, "name", None) or obj.user.email


class DashboardLowStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductVariation
        fields = ["id", "product_name", "size", "sku", "stock_quantity"]