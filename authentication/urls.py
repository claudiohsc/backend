from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GoogleLoginView, 
    LogoutView, 
    MeView, 
    TokenRefreshView,
    CustomerCRMViewSet
)

app_name = "authentication"

router = DefaultRouter()
router.register(r'crm/customers', CustomerCRMViewSet, basename='crm-customers')

urlpatterns = [
    path("google/", GoogleLoginView.as_view(), name="google-login"),

    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    path("logout/", LogoutView.as_view(), name="logout"),

    path("me/", MeView.as_view(), name="me"),
    
    path("", include(router.urls)),
]