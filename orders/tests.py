from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import UserProfile, UserRole

User = get_user_model()


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
