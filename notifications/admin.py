from django.contrib import admin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "template_name",
        "recipient_email",
        "status",
        "provider",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "template_name", "provider")
    search_fields = ("recipient_email", "subject")
    readonly_fields = (
        "context",
        "provider_message_id",
        "error_message",
        "sent_at",
        "created_at",
        "updated_at",
    )
