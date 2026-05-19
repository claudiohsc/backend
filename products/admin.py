from django.contrib import admin

from .models import Category, Product, ProductVariation


class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_price", "is_active")
    search_fields = ("name",)
    list_filter = ("category", "is_active")
    inlines = [ProductVariationInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
