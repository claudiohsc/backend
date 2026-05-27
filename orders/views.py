import datetime

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema

from authentication.permissions import IsStaffOrSuperuser

from .models import CustomerOrder, OrderStatus, Cart, OrderItem, PaymentStatus, Payment
from .serializers import DashboardLowStockSerializer, DashboardRecentOrderSerializer
from products.models import ProductVariation
from .services import create_infinitepay_checkout, check_payment_status

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

class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        cart = Cart.objects.filter(user=user, status='ACTIVE').prefetch_related('items__variation__product').first()

        if not cart or not cart.items.exists():
            return Response({"success": False, "message": "Carrinho vazio."}, status=status.HTTP_400_BAD_REQUEST)

        address_id = request.data.get('address_id')
        if not address_id:
            return Response({"success": False, "message": "Endereço não informado."}, status=status.HTTP_400_BAD_REQUEST)

        address = user.addresses.filter(id=address_id).first()
        if not address:
            return Response({"success": False, "message": "Endereço inválido."}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(item.quantity * item.unit_price for item in cart.items.all())
        shipping_cost = request.data.get('shipping_cost', 0.00)
        total_amount = float(subtotal) + float(shipping_cost)

        order = CustomerOrder.objects.create(
            user=user,
            address=address,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            shipping_zip_code=address.zip_code,
            shipping_street=address.street,
            shipping_number=address.address_number,
            shipping_complement=address.complement,
            shipping_neighborhood=address.neighborhood,
            shipping_city=address.city,
            shipping_state=address.state
        )

        for item in cart.items.all():
            if item.variation.stock_quantity < item.quantity:
                transaction.set_rollback(True)
                return Response(
                    {"success": False, "message": f"Estoque insuficiente para {item.variation.product.name}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.variation.stock_quantity -= item.quantity
            item.variation.save()

            OrderItem.objects.create(
                order=order,
                variation=item.variation,
                quantity=item.quantity,
                unit_price=item.unit_price,
                product_name=f"{item.variation.product.name} - {item.variation.size}",
                sku_snapshot=item.variation.sku
            )

        cart.status = 'FINISHED'
        cart.save()

        try:
            checkout_url = create_infinitepay_checkout(order, request)
            return Response({"success": True, "checkout_url": checkout_url}, status=status.HTTP_201_CREATED)
        except Exception:
            transaction.set_rollback(True)
            return Response(
                {"success": False, "message": "Não foi possível iniciar o checkout da InfinitePay."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentSuccessRedirectView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        order_nsu = request.query_params.get("order_nsu")
        transaction_nsu = request.query_params.get("transaction_nsu")
        slug = request.query_params.get("slug")

        if not all([order_nsu, transaction_nsu, slug]):
            return Response({"message": "Faltam parâmetros de validação."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = CustomerOrder.objects.get(id=order_nsu)
        except CustomerOrder.DoesNotExist:
            return Response({"message": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if order.status != OrderStatus.PAID:
            check_data = check_payment_status(order_nsu, transaction_nsu, slug)
            
            if check_data and check_data.get("paid") is True:
                order.payment.gateway_transaction_id = transaction_nsu
                order.payment.status = PaymentStatus.PAID
                order.payment.save()
                order.status = OrderStatus.PAID
                order.save()

        if order.status == OrderStatus.PAID:
            return Response({"message": "Pagamento confirmado com sucesso!", "order_id": order_nsu})
        
        return Response({"message": "Pagamento pendente ou em processamento.", "order_id": order_nsu})