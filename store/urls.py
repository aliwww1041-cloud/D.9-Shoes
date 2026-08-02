from django.urls import path
from . import views

urlpatterns = [
    # Main / Home & Details
    path('', views.home, name='home'),
    path('', views.home, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart & Checkout Actions
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    

    # Auth Links
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),

    # JazzCash Integration
    path('pay-jazzcash/<int:order_id>/', views.initiate_jazzcash_payment, name='initiate_jazzcash'),
    path('jazzcash-callback/', views.jazzcash_callback, name='jazzcash_callback'),
    path('remove-from-cart/<str:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('category/<str:slug>/', views.category_products, name='category_products'),
]