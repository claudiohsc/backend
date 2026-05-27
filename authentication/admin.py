from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "name",
            "google_id",
            "avatar_url",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    """Admin customizado para o modelo User com Google OAuth."""

    list_display = [
        "email",
        "name",
        "google_id",
        "is_new_user",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_new_user", "is_active", "is_staff", "created_at"]
    search_fields = ["email", "name", "google_id"]
    ordering = ["-created_at"]
    readonly_fields = [
        "google_id",
        "avatar_url",
        "created_at",
        "updated_at",
        "last_login",
    ]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações Pessoais", {"fields": ("name", "avatar_url")}),
        ("Google OAuth", {"fields": ("google_id",)}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "created_at", "updated_at")}),
        ("Flags", {"fields": ("is_new_user",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )
