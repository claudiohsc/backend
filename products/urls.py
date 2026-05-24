from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    DropCampaignDetailView,
    DropCampaignListCreateView,
    DropProductManageView,
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

    # GET (público) - Lista drops / POST (admin) - Cria drop
    path(
        "drops/",
        DropCampaignListCreateView.as_view(),
        name="drop-list-create",
    ),
    # GET (público) - Detalhe com produtos / PUT, DELETE (admin)
    path(
        "drops/<uuid:pk>/",
        DropCampaignDetailView.as_view(),
        name="drop-detail",
    ),
    # POST (admin) - Vincula produto ao drop / DELETE (admin) - Desvincula
    path(
        "drops/<uuid:drop_id>/products/<uuid:product_id>/",
        DropProductManageView.as_view(),
        name="drop-product-manage",
    ),

    # GET - Resumo de stock (legado)
    path("inventory/", inventory_summary, name="inventory_summary"),
]
