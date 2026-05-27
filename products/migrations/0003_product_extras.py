import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0002_dropcampaign_extra_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="base_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.RemoveField(
            model_name="productimage",
            name="url",
        ),
        migrations.AddField(
            model_name="productimage",
            name="image",
            field=models.ImageField(
                default="",
                upload_to="products/images/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    )
                ],
                verbose_name="Imagem do produto",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="productimage",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=None),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="productimage",
            name="display_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="productimage",
            options={"ordering": ["display_order", "created_at"]},
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("ENTRADA", "Entrada"), ("SAIDA", "Saída")],
                        max_length=10,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("COMPRA", "Compra"),
                            ("DEVOLUCAO", "Devolução"),
                            ("AJUSTE", "Ajuste"),
                            ("PERDA", "Perda/Avaria"),
                            ("VENDA", "Venda"),
                            ("OUTRO", "Outro"),
                        ],
                        max_length=20,
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "variation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_movements",
                        to="products.productvariation",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
