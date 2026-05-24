import django.core.validators
from django.db import migrations, models
from django.utils.text import slugify


def slugify_existing_drops(apps, schema_editor):
    """Preenche slug dos drops existentes a partir do name."""
    DropCampaign = apps.get_model("products", "DropCampaign")
    used_slugs = set()
    for drop in DropCampaign.objects.all():
        base = slugify(drop.name) or "drop"
        candidate = base
        suffix = 2
        while (
            candidate in used_slugs
            or DropCampaign.objects.exclude(pk=drop.pk).filter(slug=candidate).exists()
        ):
            candidate = f"{base}-{suffix}"
            suffix += 1
        drop.slug = candidate
        drop.save(update_fields=["slug"])
        used_slugs.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dropcampaign',
            name='banner',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='drops/banners/',
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
                verbose_name='Banner da campanha',
            ),
        ),
        migrations.AddField(
            model_name='dropcampaign',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='dropcampaign',
            name='is_public',
            field=models.BooleanField(default=True, verbose_name='Drop público'),
        ),
        migrations.AddField(
            model_name='dropcampaign',
            name='slug',
            field=models.SlugField(max_length=255, null=True, unique=True),
        ),
        migrations.RunPython(slugify_existing_drops, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='dropcampaign',
            name='slug',
            field=models.SlugField(max_length=255, unique=True),
        ),
    ]
