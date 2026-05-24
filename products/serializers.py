from django.utils.text import slugify
from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer de Category — usado em list, detail, create e update (PUT)."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_name = validated_data.get("name", instance.name)
        slug_sent = bool(validated_data.get("slug"))
        if new_name != instance.name and not slug_sent:
            validated_data["slug"] = slugify(new_name)
        return super().update(instance, validated_data)
