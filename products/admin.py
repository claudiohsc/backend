from django.contrib import admin
from .models import Category, DropCampaign, Product, ProductVariation

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'is_active')
    search_fields = ('name',)
    list_filter = ('category', 'is_active')
    inlines = [ProductVariationInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}


@admin.register(DropCampaign)
class DropCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name", "slug",
        "launch_date", "end_date",
        "is_public", "is_active",
    )
    list_filter = ("is_active", "is_public")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}