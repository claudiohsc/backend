from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, DropCampaign, Product


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


class ProductNestedSerializer(serializers.ModelSerializer):
    """Resumo de Product usado dentro do detalhe de DropCampaign."""

    class Meta:
        model = Product
        fields = ["id", "name", "base_price", "is_active"]
        read_only_fields = fields


class DropCampaignSerializer(serializers.ModelSerializer):
    """Serializer de DropCampaign — list, create e update (PUT)."""

    class Meta:
        model = DropCampaign
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_public",
            "banner",
            "launch_date",
            "end_date",
            "max_quantity",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    def validate_banner(self, value):
        max_mb = 5
        if value and value.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(
                f"Banner não pode passar de {max_mb}MB."
            )
        return value

    def validate(self, attrs):
        launch = attrs.get("launch_date")
        end = attrs.get("end_date")
        if launch and end and end <= launch:
            raise serializers.ValidationError(
                {"end_date": "end_date deve ser posterior a launch_date."}
            )
        return attrs

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_name = validated_data.get("name", instance.name)
        slug_sent = bool(validated_data.get("slug"))
        if new_name != instance.name and not slug_sent:
            validated_data["slug"] = slugify(new_name)

        new_banner = validated_data.get("banner", serializers.empty)
        replacing_banner = (
            new_banner is not serializers.empty
            and instance.banner
            and new_banner != instance.banner
        )
        if replacing_banner:
            instance.banner.delete(save=False)
        return super().update(instance, validated_data)


class DropCampaignDetailSerializer(DropCampaignSerializer):
    """Detalhe do drop com produtos aninhados (resumidos)."""

    products = ProductNestedSerializer(many=True, read_only=True)

    class Meta(DropCampaignSerializer.Meta):
        fields = DropCampaignSerializer.Meta.fields + ["products"]
