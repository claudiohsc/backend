from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime

from authentication.permissions import IsAdmin
from orders.models import CustomerOrder, OrderStatus
from products.models import ProductVariation

User = get_user_model()

class AdminDashboardView(APIView):
    """
    Endpoint consolidado para o Dashboard Administrativo (UC05).
    Utiliza os campos nativos do Django (is_staff) para distinguir admins de clientes.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
        
        valid_orders_period = CustomerOrder.objects.filter(
            created_at__gte=thirty_days_ago,
            status__in=[OrderStatus.PAID, OrderStatus.PREPARING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
        )
        
        total_revenue = valid_orders_period.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders = valid_orders_period.count()
        
        ticket_medio = (total_revenue / total_orders) if total_orders > 0 else 0

        total_clientes = User.objects.filter(is_staff=False, is_superuser=False).count()
        novos_clientes = User.objects.filter(
            is_staff=False, 
            is_superuser=False,
            created_at__gte=thirty_days_ago
        ).count()

        recent_orders_qs = (
            CustomerOrder.objects
            .select_related('user')
            .order_by('-created_at')[:10]
        )
        recent_orders = [
            {
                "id": str(order.id),
                "customer_name": order.user.name if hasattr(order.user, 'name') else order.user.email,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at
            } for order in recent_orders_qs
        ]

        low_stock_qs = ProductVariation.objects.filter(
            stock_quantity__lt=10
        ).select_related('product')
        
        low_stock_alerts = [
            {
                "variation_id": str(variation.id),
                "product_name": variation.product.name,
                "size": variation.size,
                "sku": variation.sku,
                "current_stock": variation.stock_quantity
            } for variation in low_stock_qs
        ]

        return Response({
            "sales_summary": {
                "period_days": 30,
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "average_ticket": round(ticket_medio, 2)
            },
            "customers_summary": {
                "total_registered": total_clientes,
                "new_in_period": novos_clientes
            },
            "recent_orders": recent_orders,
            "low_stock_alerts": low_stock_alerts
        }, status=status.HTTP_200_OK)