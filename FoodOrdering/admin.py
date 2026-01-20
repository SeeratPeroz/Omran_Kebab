from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Product,
    TableReservation,
    Order,
    OrderItem,
    OptionGroup,
    Option,
    ProductOptionGroup,
    OrderItemOption,
)

# -------------------------
# CATEGORY / PRODUCT
# -------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


class ProductOptionGroupInline(admin.TabularInline):
    model = ProductOptionGroup
    extra = 0
    autocomplete_fields = ("group",)
    fields = ("group", "sort_order", "is_required", "min_select", "max_select")
    ordering = ("sort_order",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "image_preview")
    list_filter = ("is_available", "category")
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    inlines = [ProductOptionGroupInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px; width:auto; border-radius:6px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Image"






# -------------------------
# OPTIONS / MODIFIERS
# -------------------------

class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    fields = ("name", "price_delta", "sort_order", "is_active")
    ordering = ("sort_order", "name")


@admin.register(OptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_required", "min_select", "max_select", "is_active", "sort_order")
    list_filter = ("is_active", "is_required")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")
    inlines = [OptionInline]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("name", "group", "price_delta", "is_active", "sort_order")
    list_filter = ("group", "is_active")
    search_fields = ("name", "group__name")
    ordering = ("group", "sort_order", "name")
    autocomplete_fields = ("group",)


# -------------------------
# ORDERS
# -------------------------

class OrderItemOptionInline(admin.TabularInline):
    model = OrderItemOption
    extra = 0
    autocomplete_fields = ("option",)
    fields = ("option", "price_delta_at_time")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)
    fields = ("product", "quantity", "price_at_time")
    readonly_fields = ()
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "full_name", "phone", "created_at", "placed_at", "total_price_display")
    list_filter = ("status", "created_at")
    search_fields = ("id", "full_name", "phone", "email")
    ordering = ("-created_at",)
    inlines = [OrderItemInline]

    def total_price_display(self, obj):
        return f"{obj.total_price():.2f} €"
    total_price_display.short_description = "Total"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "price_at_time", "unit_total_display", "total_price_display")
    list_filter = ("order__status",)
    search_fields = ("order__id", "product__name")
    autocomplete_fields = ("order", "product")
    inlines = [OrderItemOptionInline]

    def unit_total_display(self, obj):
        return f"{obj.unit_total():.2f} €"
    unit_total_display.short_description = "Unit total"

    def total_price_display(self, obj):
        return f"{obj.total_price():.2f} €"
    total_price_display.short_description = "Line total"


@admin.register(OrderItemOption)
class OrderItemOptionAdmin(admin.ModelAdmin):
    list_display = ("order_item", "option", "price_delta_at_time")
    list_filter = ("option__group",)
    search_fields = ("order_item__order__id", "option__name", "option__group__name")
    autocomplete_fields = ("order_item", "option")


# Optional: if you want to manage ProductOptionGroup separately too
@admin.register(ProductOptionGroup)
class ProductOptionGroupAdmin(admin.ModelAdmin):
    list_display = ("product", "group", "sort_order", "is_required", "min_select", "max_select")
    list_filter = ("group",)
    search_fields = ("product__name", "group__name")
    autocomplete_fields = ("product", "group")
    ordering = ("product", "sort_order")

# -------------------------
# RESERVATIONS
# -------------------------

@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "date", "time", "people", "status", "created_at")
    list_filter = ("status", "date")
    search_fields = ("name", "phone", "email")
    ordering = ("-created_at",)
