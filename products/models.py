import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class DropCampaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True, verbose_name="Drop público")
    banner = models.ImageField(
        upload_to="drops/banners/",
        null=True,
        blank=True,
        verbose_name="Banner da campanha",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])
        ],
    )
    launch_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    max_quantity = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.banner:
            self.banner.delete(save=False)
        return super().delete(*args, **kwargs)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drop = models.ForeignKey(
        DropCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductVariation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variations"
    )
    size = models.CharField(max_length=50)
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.size}"


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to="products/images/",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])
        ],
        verbose_name="Imagem do produto",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"{self.product.name} #{self.display_order}"

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        return super().delete(*args, **kwargs)


class StockMovementKind(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SAIDA = "SAIDA", "Saída"


class StockMovementReason(models.TextChoices):
    COMPRA = "COMPRA", "Compra"
    DEVOLUCAO = "DEVOLUCAO", "Devolução"
    AJUSTE = "AJUSTE", "Ajuste"
    PERDA = "PERDA", "Perda/Avaria"
    VENDA = "VENDA", "Venda"
    OUTRO = "OUTRO", "Outro"


class StockMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variation = models.ForeignKey(
        ProductVariation,
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    kind = models.CharField(max_length=10, choices=StockMovementKind.choices)
    reason = models.CharField(max_length=20, choices=StockMovementReason.choices)
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.quantity} ({self.reason})"
