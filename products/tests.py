"""
Testes para os endpoints de Category.

Executar com:
    pytest products/tests.py -v
"""

import uuid

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import UserProfile, UserRole

from .models import Category

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_user(email, role=UserRole.CUSTOMER, name="User"):
    """Cria um utilizador com perfil associado para uso nos testes."""
    user = User.objects.create_user(email=email, name=name)
    UserProfile.objects.create(user=user, role=role)
    return user


def auth_header(user):
    """Devolve o header Authorization Bearer para o utilizador."""
    token = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


# ─── List & Create ────────────────────────────────────────────────────────────


class CategoryListCreateTests(APITestCase):
    """Testes para GET/POST /api/products/categories/."""

    url = "/api/products/categories/"

    def setUp(self):
        self.admin = make_user("admin@x.com", role=UserRole.ADMIN, name="Admin")
        self.customer = make_user("c@x.com", role=UserRole.CUSTOMER, name="Cliente")
        Category.objects.create(name="Camisetas", slug="camisetas")
        Category.objects.create(name="Bonés", slug="bones")

    def test_listagem_publica_sem_autenticacao(self):
        """Deve listar categorias paginadas sem token."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertIn("results", data)

    def test_admin_cria_categoria_com_slug_auto(self):
        """POST de admin sem slug deve auto-gerar a partir do name."""
        response = self.client.post(
            self.url,
            {"name": "Calças Cargo"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["slug"], "calcas-cargo")

    def test_admin_cria_com_slug_explicito(self):
        """POST com slug enviado deve usar o slug fornecido."""
        response = self.client.post(
            self.url,
            {"name": "Acessórios", "slug": "acess"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["slug"], "acess")

    def test_cliente_nao_pode_criar(self):
        """POST de utilizador não-admin deve retornar 403."""
        response = self.client.post(
            self.url,
            {"name": "X"},
            format="json",
            **auth_header(self.customer),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sem_token_nao_pode_criar(self):
        """POST sem Authorization header deve retornar 401."""
        response = self.client.post(self.url, {"name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nome_duplicado_retorna_400(self):
        """POST com name já existente deve retornar 400."""
        response = self.client.post(
            self.url,
            {"name": "Camisetas"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Detail / Update / Delete ─────────────────────────────────────────────────


class CategoryDetailTests(APITestCase):
    """Testes para GET/PUT/DELETE /api/products/categories/{id}/."""

    def setUp(self):
        self.admin = make_user("admin@x.com", role=UserRole.ADMIN, name="Admin")
        self.customer = make_user("c@x.com", role=UserRole.CUSTOMER, name="Cliente")
        self.category = Category.objects.create(name="Camisetas", slug="camisetas")
        self.url = f"/api/products/categories/{self.category.id}/"

    def test_detalhe_publico(self):
        """GET deve retornar a categoria sem exigir autenticação."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Camisetas")

    def test_detalhe_404_quando_id_inexistente(self):
        """GET com UUID inexistente deve retornar 404."""
        response = self.client.get(f"/api/products/categories/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_admin_regenera_slug_quando_name_muda(self):
        """PUT mudando o name e sem enviar slug deve regenerar o slug."""
        response = self.client.put(
            self.url,
            {"name": "Camisas Polo"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["slug"], "camisas-polo")

    def test_put_admin_mantem_slug_explicito(self):
        """PUT com slug explícito deve usar o slug enviado mesmo que name mude."""
        response = self.client.put(
            self.url,
            {"name": "Camisas Polo", "slug": "polo-custom"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["slug"], "polo-custom")

    def test_put_admin_mantem_slug_se_name_nao_muda(self):
        """PUT sem alterar name não deve regenerar o slug."""
        response = self.client.put(
            self.url,
            {"name": "Camisetas"},
            format="json",
            **auth_header(self.admin),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["slug"], "camisetas")

    def test_cliente_nao_pode_atualizar(self):
        """PUT de utilizador não-admin deve retornar 403."""
        response = self.client.put(
            self.url,
            {"name": "X"},
            format="json",
            **auth_header(self.customer),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_pode_remover(self):
        """DELETE de admin deve apagar a categoria e retornar 204."""
        response = self.client.delete(self.url, **auth_header(self.admin))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=self.category.id).exists())

    def test_cliente_nao_pode_remover(self):
        """DELETE de utilizador não-admin deve retornar 403."""
        response = self.client.delete(self.url, **auth_header(self.customer))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
