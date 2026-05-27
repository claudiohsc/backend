import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from authentication.models import Address, UserProfile, UserRole
from products.models import Category, Product, ProductVariation
from orders.models import Cart, CartItem, CustomerOrder, Payment, OrderStatus, PaymentStatus
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class CheckoutAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testador@shio.com",
            name="Testador",
            password="senha_forte_123"
        )
        self.client.force_authenticate(user=self.user)

        self.address = Address.objects.create(
            user=self.user,
            zip_code="71000000",
            street="Rua Teste",
            address_number="123",
            neighborhood="Centro",
            city="Brasília",
            state="DF"
        )

        self.category = Category.objects.create(name="Roupas", slug="roupas")
        self.product = Product.objects.create(
            category=self.category,
            name="Camiseta Teste",
            base_price=100.00
        )
        self.variation = ProductVariation.objects.create(
            product=self.product,
            size="M",
            sku="TESTE-M",
            stock_quantity=10
        )

        self.cart = Cart.objects.create(user=self.user, status="ACTIVE")
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            variation=self.variation,
            quantity=2,
            unit_price=100.00
        )

        self.url = '/api/orders/checkout/'

    @patch('orders.views.create_infinitepay_checkout')
    def test_checkout_sucesso_gera_pedido_e_reduz_estoque(self, mock_create_checkout):
        """Deve retornar 201, criar o pedido, finalizar o carrinho e deduzir estoque."""
        mock_create_checkout.return_value = "https://pay.infinitepay.io/mock-url"

        payload = {
            "address_id": str(self.address.id),
            "shipping_cost": 15.00
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["checkout_url"], "https://pay.infinitepay.io/mock-url")
        
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, "FINISHED")

        self.variation.refresh_from_db()
        self.assertEqual(self.variation.stock_quantity, 8)

        order = CustomerOrder.objects.get(user=self.user)
        self.assertEqual(order.status, OrderStatus.AWAITING_PAYMENT)
        self.assertEqual(order.total_amount, 215.00)

    def test_checkout_com_carrinho_vazio_retorna_400(self):
        """Deve retornar 400 se o usuário não tiver itens no carrinho ativo."""
        self.cart.items.all().delete()

        payload = {
            "address_id": str(self.address.id),
            "shipping_cost": 15.00
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomerOrder.objects.count(), 0)

    def test_checkout_sem_estoque_faz_rollback_e_retorna_400(self):
        """Deve barrar a compra e garantir que o carrinho continua ativo e o estoque intacto."""
        self.cart_item.quantity = 20
        self.cart_item.save()

        payload = {
            "address_id": str(self.address.id),
            "shipping_cost": 15.00
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, "ACTIVE")
        
        self.variation.refresh_from_db()
        self.assertEqual(self.variation.stock_quantity, 10)

    @patch('orders.views.create_infinitepay_checkout')
    def test_checkout_falha_gateway_faz_rollback(self, mock_create_checkout):
        """Deve proteger o banco de dados se a API da InfinitePay cair."""
        mock_create_checkout.side_effect = Exception("InfinitePay Timeout")

        payload = {
            "address_id": str(self.address.id),
            "shipping_cost": 15.00
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(CustomerOrder.objects.count(), 0)
        
        self.variation.refresh_from_db()
        self.assertEqual(self.variation.stock_quantity, 10)


class PaymentSuccessRedirectTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testador2@shio.com", password="123")
        
        self.order = CustomerOrder.objects.create(
            user=self.user,
            subtotal=100.00,
            total_amount=100.00,
            status=OrderStatus.AWAITING_PAYMENT,
            shipping_zip_code="000",
            shipping_street="X",
            shipping_number="1",
            shipping_neighborhood="Y",
            shipping_city="Z",
            shipping_state="DF"
        )
        
        self.payment = Payment.objects.create(
            order=self.order,
            method="CREDIT_CARD",
            status=PaymentStatus.PROCESSING,
            total_amount=100.00
        )

        self.url = '/api/orders/pagamento-sucesso/'

    @patch('orders.views.check_payment_status')
    def test_pagamento_confirmado_pela_infinitepay(self, mock_check_payment):
        """Deve atualizar o pedido para PAID se o gateway confirmar."""
        mock_check_payment.return_value = {"paid": True}

        response = self.client.get(self.url, {
            "order_nsu": str(self.order.id),
            "transaction_nsu": "TRANS123",
            "slug": "FATURA123"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.payment.status, PaymentStatus.PAID)
        self.assertEqual(self.payment.gateway_transaction_id, "TRANS123")

    @patch('orders.views.check_payment_status')
    def test_pagamento_nao_confirmado_mantem_pendente(self, mock_check_payment):
        """Deve ignorar fraude se o gateway informar que não foi pago."""
        mock_check_payment.return_value = {"paid": False}

        response = self.client.get(self.url, {
            "order_nsu": str(self.order.id),
            "transaction_nsu": "FRAUDE123",
            "slug": "FATURA123"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.AWAITING_PAYMENT)

    def test_parametros_faltando_retorna_400(self):
        """Deve retornar erro se a query string estiver incompleta."""
        response = self.client.get(self.url, {"order_nsu": str(self.order.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pedido_nao_encontrado_retorna_404(self):
        """Deve retornar 404 para um UUID inexistente."""
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(self.url, {
            "order_nsu": fake_uuid,
            "transaction_nsu": "TRANS123",
            "slug": "FATURA123"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)




class AdminDashboardViewTests(APITestCase):
    """Testes para o endpoint GET /api/orders/dashboard/summary/."""

    url = "/api/orders/dashboard/summary/"

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@x.com", name="Admin", is_staff=True
        )
        UserProfile.objects.create(user=self.admin, role=UserRole.ADMIN)

        self.customer = User.objects.create_user(email="c@x.com", name="Cliente")
        UserProfile.objects.create(user=self.customer, role=UserRole.CUSTOMER)

    def auth_header(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_admin_acessa_dashboard_com_sucesso(self):
        """Admin deve poder aceder e receber o formato correto do dashboard."""
        response = self.client.get(self.url, **self.auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("sales_summary", data)
        self.assertIn("customers_summary", data)
        self.assertIn("recent_orders", data)
        self.assertIn("low_stock_alerts", data)

    def test_cliente_nao_acessa_dashboard(self):
        """Utilizador sem permissão is_staff recebe 403."""
        response = self.client.get(self.url, **self.auth_header(self.customer))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

