from django.contrib import admin
from .models import Order, Product, Category, ProductVariant

# Pehle se agar registered ho toh error na aaye
try:
    admin.site.unregister(Order)
except admin.sites.NotRegistered:
    pass

# Orders Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'city', 'payment_method', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'payment_method', 'status')
    search_fields = ('full_name', 'phone', 'email')
    ordering = ('-created_at',)

# Product aur baqi models register karein
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(ProductVariant)