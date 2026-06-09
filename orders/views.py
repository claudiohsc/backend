import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsStaffOrSuperUser
from products.models import ProductVariation

from .models import (
    Cart,
    CustomerOrder,
    OrderItem,
    OrderStatus,
    OrderStatusLog,
    PaymentStatus,
)
from .serializers import (
    DashboardLowStockSerializer,
    DashboardRecentOrderSerializer,
    OrderDetailSerializer,
    OrderStatusUpdateSerializer,
)
from .services import check_payment_status, create_infinitepay_checkout

User = get_user_model()


class AdminDashboardView(APIView):
    """
    Endpoint consolidado para o Dashboard Administrativo (UC05).
    GET /api/orders/dashboard/summary/
    Restrito a is_staff ou is_superuser.
    """

    permission_classes = [IsStaffOrSuperUser]

    @extend_schema(
        description="Endpoint consolidado para o Dashboard Administrativo (UC05).",
        responses={
            200: inline_serializer(
                name="DashboardSummaryResponse",
                fields={
                    "sales_summary": inline_serializer(
                        name="DashboardSalesSummary",
                        fields={
                            "period_days": serializers.IntegerField(),
                            "total_revenue": serializers.DecimalField(
                                max_digits=10, decimal_places=2
                            ),
                            "total_orders": serializers.IntegerField(),
                            "average_ticket": serializers.DecimalField(
                                max_digits=10, decimal_places=2
                            ),
                        },
                    ),
                    "customers_summary": inline_serializer(
                        name="DashboardCustomersSummary",
                        fields={
                            "total_registered": serializers.IntegerField(),
                            "new_in_period": serializers.IntegerField(),
                        },
                    ),
                    "recent_orders": DashboardRecentOrderSerializer(many=True),
                    "low_stock_alerts": DashboardLowStockSerializer(many=True),
                },
            )
        },
    )
    def get(self, request):
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

        active_statuses = [
            OrderStatus.PAID,
            OrderStatus.PREPARING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        valid_orders_period = CustomerOrder.objects.filter(
            created_at__gte=thirty_days_ago,
            status__in=active_statuses,
        )
        total_revenue = (
            valid_orders_period.aggregate(total=Sum("total_amount"))["total"] or 0
        )
        total_orders = valid_orders_period.count()
        average_ticket = (
            round(total_revenue / total_orders, 2) if total_orders > 0 else 0
        )

        customer_filter = {"is_staff": False, "is_superuser": False}
        total_clientes = User.objects.filter(**customer_filter).count()
        novos_clientes = User.objects.filter(
            **customer_filter,
            created_at__gte=thirty_days_ago,
        ).count()

        recent_orders_qs = (
            CustomerOrder.objects.filter(status__in=active_statuses)
            .select_related("user")
            .order_by("-created_at")[:10]
        )
        recent_orders = DashboardRecentOrderSerializer(recent_orders_qs, many=True).data

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


class AdminOrderListView(APIView):
    """
    GET /api/orders/admin/
    Lista pedidos para o painel admin com filtro por `status`.
    """

    permission_classes = [IsStaffOrSuperUser]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                description="Filtra pedidos pelo status (ex: PAID, SHIPPED)",
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: DashboardRecentOrderSerializer(many=True)},
    )
    def get(self, request):
        status_q = request.query_params.get("status")
        qs = CustomerOrder.objects.select_related("user").order_by("-created_at")
        if status_q:
            qs = qs.filter(status=status_q)

        data = DashboardRecentOrderSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class AdminOrderDetailView(APIView):
    """
    GET / PATCH /api/orders/admin/{order_id}/
    Recupera detalhes do pedido e permite atualização de status/tracking.
    """

    permission_classes = [IsStaffOrSuperUser]

    @extend_schema(
        responses={200: OrderDetailSerializer},
    )
    def get(self, request, order_id):
        try:
            order = (
                CustomerOrder.objects.select_related("user", "address", "payment")
                .prefetch_related("items__variation__product")
                .get(id=order_id)
            )
        except CustomerOrder.DoesNotExist:
            return Response({"message": "Pedido não encontrado."}, status=404)

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=OrderStatusUpdateSerializer,
        responses={
            200: OrderDetailSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def patch(self, request, order_id):
        try:
            order = CustomerOrder.objects.select_related("payment").get(id=order_id)
        except CustomerOrder.DoesNotExist:
            return Response({"message": "Pedido não encontrado."}, status=404)

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_value = serializer.validated_data.get("status")
        tracking_code = serializer.validated_data.get("tracking_code")
        comment = serializer.validated_data.get("comment")

        # Rules: cannot cancel if payment already PAID
        if status_value == OrderStatus.CANCELED:
            if (
                hasattr(order, "payment")
                and order.payment
                and order.payment.status == PaymentStatus.PAID
            ):
                return Response(
                    {
                        "message": "Não é possível cancelar um pedido com pagamento confirmado."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # If shipping, require tracking code
        if status_value == OrderStatus.SHIPPED and not tracking_code:
            return Response(
                {"message": "Tracking code obrigatório ao enviar pedido."}, status=400
            )

        previous_status = order.status
        order.status = status_value
        if tracking_code:
            order.tracking_code = tracking_code

        order.save()

        if (
            status_value == OrderStatus.CANCELED
            and hasattr(order, "payment")
            and order.payment
        ):
            if order.payment.status != PaymentStatus.PAID:
                order.payment.status = PaymentStatus.FAILED
                order.payment.save()

        OrderStatusLog.objects.create(
            order=order,
            changed_by=request.user,
            previous_status=previous_status,
            new_status=status_value,
            tracking_code=tracking_code,
            comment=comment,
        )

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Finalizar Compra e Gerar Link InfinitePay",
        description=(
            "Lê o carrinho ativo do utilizador autenticado e verifica o estoque disponível. "
            "Gera o pedido (CustomerOrder), faz o snapshot do endereço de entrega e debita o estoque. "
            "Por fim, comunica-se com a API da InfinitePay para gerar o link de checkout.\n\n"
            "**Fluxo:**\n"
            "1. Envie o `address_id` (UUID do endereço do perfil) e o `shipping_cost`.\n"
            "2. O backend valida os itens e gera a cobrança.\n"
            "3. O utilizador é redirecionado para a `checkout_url` retornada."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "address_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "UUID do endereço de entrega salvo no perfil",
                    },
                    "shipping_cost": {
                        "type": "number",
                        "format": "float",
                        "description": "Valor calculado do frete (em Reais)",
                    },
                },
                "required": ["address_id"],
            }
        },
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    @transaction.atomic
    def post(self, request):
        user = request.user
        cart = (
            Cart.objects.filter(user=user, status="ACTIVE")
            .prefetch_related("items__variation__product")
            .first()
        )

        if not cart or not cart.items.exists():
            return Response(
                {"success": False, "message": "Carrinho vazio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        address_id = request.data.get("address_id")
        if not address_id:
            return Response(
                {"success": False, "message": "Endereço não informado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        address = user.addresses.filter(id=address_id).first()
        if not address:
            return Response(
                {"success": False, "message": "Endereço inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subtotal = sum(item.quantity * item.unit_price for item in cart.items.all())
        shipping_cost = request.data.get("shipping_cost", 0.00)
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
            shipping_state=address.state,
        )

        for item in cart.items.all():
            if item.variation.stock_quantity < item.quantity:
                transaction.set_rollback(True)
                return Response(
                    {
                        "success": False,
                        "message": f"Estoque insuficiente para {item.variation.product.name}.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item.variation.stock_quantity -= item.quantity
            item.variation.save()

            OrderItem.objects.create(
                order=order,
                variation=item.variation,
                quantity=item.quantity,
                unit_price=item.unit_price,
                product_name=f"{item.variation.product.name} - {item.variation.size}",
                sku_snapshot=item.variation.sku,
            )

        cart.status = "FINISHED"
        cart.save()

        try:
            checkout_url = create_infinitepay_checkout(order, request)
            return Response(
                {"success": True, "checkout_url": checkout_url},
                status=status.HTTP_201_CREATED,
            )
        except Exception:
            transaction.set_rollback(True)
            return Response(
                {
                    "success": False,
                    "message": "Não foi possível iniciar o checkout da InfinitePay.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentSuccessRedirectView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirmação de Pagamento (Redirect InfinitePay)",
        description=(
            "Rota de fallback acessada pelo navegador do cliente após o pagamento na InfinitePay. "
            "Recebe os parâmetros via query string, consulta o status real da transação no servidor "
            "da InfinitePay e efetiva a baixa do pedido (muda status para PAID) caso aprovado.\n\n"
            "⚠️ *Não envia token JWT. O front-end deve exibir uma tela de 'Processando' ao carregar esta rota.*"
        ),
        parameters=[
            OpenApiParameter(
                name="order_nsu",
                type=str,
                location=OpenApiParameter.QUERY,
                description="UUID do pedido gerado no nosso sistema",
            ),
            OpenApiParameter(
                name="transaction_nsu",
                type=str,
                location=OpenApiParameter.QUERY,
                description="ID único da transação gerado pela InfinitePay",
            ),
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Código da fatura gerado pela InfinitePay",
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        order_nsu = request.query_params.get("order_nsu")
        transaction_nsu = request.query_params.get("transaction_nsu")
        slug = request.query_params.get("slug")

        if not all([order_nsu, transaction_nsu, slug]):
            return Response(
                {"message": "Faltam parâmetros de validação."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = CustomerOrder.objects.get(id=order_nsu)
        except CustomerOrder.DoesNotExist:
            return Response(
                {"message": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

        if order.status != OrderStatus.PAID:
            check_data = check_payment_status(order_nsu, transaction_nsu, slug)

            if check_data and check_data.get("paid") is True:
                order.payment.gateway_transaction_id = transaction_nsu
                order.payment.status = PaymentStatus.PAID
                order.payment.save()
                order.status = OrderStatus.PAID
                order.save()

        if order.status == OrderStatus.PAID:
            return Response(
                {"message": "Pagamento confirmado com sucesso!", "order_id": order_nsu}
            )

        return Response(
            {
                "message": "Pagamento pendente ou em processamento.",
                "order_id": order_nsu,
            }
        )
