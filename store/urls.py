from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView,
    CategoryListView, ProductListView, ProductDetailView,
    CartView, CartItemCreateView, CartItemDetailView,
    OrderListView, CheckoutView, PaymentSuccessView, PaymentFailView, PaymentCancelView 
    ) 

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    # কার্ট রাউটস (BM-5)
    path('cart/', CartView.as_view(), name='cart-detail'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-item-add'),
    path('cart/items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    # অর্ডার ও পেমেন্ট রাউটস (এই ৫টি লাইন যোগ করে Ctrl + S দিয়ে সেভ করুন):
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('payment/success/', PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/fail/', PaymentFailView.as_view(), name='payment-fail'),
    path('payment/cancel/', PaymentCancelView.as_view(), name='payment-cancel'),
]

