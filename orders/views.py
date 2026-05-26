import datetime

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from authentication.permissions import IsStaffOrSuperuser

from .models import CustomerOrder, OrderStatus
from .serializers import DashboardLowStockSerializer, DashboardRecentOrderSerializer
from products.models import ProductVariation

User = get_user_model()


class AdminDashboardView(APIView):
    """
    Endpoint consolidado para o Dashboard Administrativo (UC05).
    GET /api/orders/dashboard/summary/
    Restrito a is_staff ou is_superuser.
    """

    permission_classes = [IsStaffOrSuperuser]

    @extend_schema(
        description="Endpoint consolidado para o Dashboard Administrativo (UC05).",
        responses={200: "Resumo do dashboard administrativo."}
    )
    def get(self, request):
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

        active_statuses = [
            OrderStatus.PAID,
            OrderStatus.PREPARING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        # Resumo de vendas — últimos 30 dias, apenas pedidos válidos
        valid_orders_period = CustomerOrder.objects.filter(
            created_at__gte=thirty_days_ago,
            status__in=active_statuses,
        )
        total_revenue = valid_orders_period.aggregate(
            total=Sum("total_amount")
        )["total"] or 0
        total_orders = valid_orders_period.count()
        average_ticket = round(total_revenue / total_orders, 2) if total_orders > 0 else 0

        # Resumo de clientes
        customer_filter = {"is_staff": False, "is_superuser": False}
        total_clientes = User.objects.filter(**customer_filter).count()
        novos_clientes = User.objects.filter(
            **customer_filter,
            created_at__gte=thirty_days_ago,
        ).count()

        # Pedidos recentes — apenas válidos, sem N+1, limite 10
        recent_orders_qs = (
            CustomerOrder.objects.filter(status__in=active_statuses)
            .select_related("user")
            .order_by("-created_at")[:10]
        )
        recent_orders = DashboardRecentOrderSerializer(recent_orders_qs, many=True).data

        # Alertas de stock baixo — ordenados por stock crescente, limite 50
        low_stock_qs = (
            ProductVariation.objects.filter(stock_quantity__lt=10)
            .select_related("product")
            .order_by("stock_quantity")[:50]
        )
        low_stock_alerts = DashboardLowStockSerializer(low_stock_qs, many=True).data

        return Response(
            {
                "sales_summary": {
                    "period_days": 30,
                    "total_revenue": total_revenue,
                    "total_orders": total_orders,
                    "average_ticket": average_ticket,
                },
                "customers_summary": {
                    "total_registered": total_clientes,
                    "new_in_period": novos_clientes,
                },
                "recent_orders": recent_orders,
                "low_stock_alerts": low_stock_alerts,
            },
            status=status.HTTP_200_OK,
        )