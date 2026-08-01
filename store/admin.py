from django.contrib import admin
from .models import Order, OrderItem, Product, Category, ProductVariant

# Order ke andar items ko tabular format mein dikhane ke liye
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'price', 'quantity')

# Order Admin Configuration
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'city', 'total_amount', 'payment_method', 'status', 'is_paid', 'created_at')
    list_filter = ('status', 'is_paid', 'payment_method', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'id')
    ordering = ('-created_at',)
    inlines = [OrderItemInline] # Is se Order kholte hi andar ke items dikhenge

# Baqi Models
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(ProductVariant)