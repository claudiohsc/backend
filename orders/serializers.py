from rest_framework import serializers
from .models import CustomerOrder
from products.models import ProductVariation

class RecentOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerOrder
        fields = ['id', 'customer_name', 'total_amount', 'status', 'created_at']

    def get_customer_name(self, obj):
        return getattr(obj.user, 'name', obj.user.email)


class LowStockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name')
    current_stock = serializers.IntegerField(source='stock_quantity')
    variation_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = ProductVariation
        fields = ['variation_id', 'product_name', 'size', 'sku', 'current_stock']