from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import GoogleLoginView, LogoutView, MeView, TokenRefreshView

app_name = "authentication"

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token-login"),

    path("google/", GoogleLoginView.as_view(), name="google-login"),

    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    path("logout/", LogoutView.as_view(), name="logout"),

    path("me/", MeView.as_view(), name="me"),
]