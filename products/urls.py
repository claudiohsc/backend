from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    inventory_summary,
)

app_name = "products"

urlpatterns = [
    # GET (público) - Lista categorias / POST (admin) - Cria categoria
    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    # GET (público) - Detalhe / PUT, DELETE (admin) - Atualiza/remove categoria
    path(
        "categories/<uuid:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),

    # GET - Resumo de stock (legado)
    path("inventory/", inventory_summary, name="inventory_summary"),
]
