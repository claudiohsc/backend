import logging

from django.db.models import Sum

from .models import Product

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 5


class InventoryService:
    @staticmethod
    def get_summary() -> dict:
        total_products = Product.objects.filter(is_active=True).count()

        aggregation = Product.objects.filter(is_active=True).aggregate(
            total_stock=Sum("variations__stock_quantity")
        )
        total_stock = aggregation["total_stock"] or 0

        low_stock_count = (
            Product.objects.filter(is_active=True)
            .annotate(stock=Sum("variations__stock_quantity"))
            .filter(stock__lte=LOW_STOCK_THRESHOLD)
            .count()
        )

        logger.info("InventoryService.get_summary chamado.")
        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": low_stock_count,
        }
