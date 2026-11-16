from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView,
    CategoryListView, ProductListView, ProductDetailView, BrandListView,
    CartView, CartItemCreateView, CartItemDetailView,
    OrderListView, CheckoutView, PaymentSuccessView, PaymentFailView, PaymentCancelView,
    AdminDashboardStatsView, AdminProductListCreateView, AdminProductDetailView,
    AdminCategoryCreateView, AdminOrderListView, AdminOrderStatusUpdateView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    path('cart/', CartView.as_view(), name='cart-detail'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-item-add'),
    path('cart/items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('payment/success/', PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/fail/', PaymentFailView.as_view(), name='payment-fail'),
    path('payment/cancel/', PaymentCancelView.as_view(), name='payment-cancel'),

    # Store Admin APIs
    path('admin-panel/stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),
    path('admin-panel/categories/', AdminCategoryCreateView.as_view(), name='admin-categories'),
    path('admin-panel/products/', AdminProductListCreateView.as_view(), name='admin-products'),
    path('admin-panel/products/<int:pk>/', AdminProductDetailView.as_view(), name='admin-product-detail'),
    path('admin-panel/orders/', AdminOrderListView.as_view(), name='admin-orders'),
    path('admin-panel/orders/<int:pk>/', AdminOrderStatusUpdateView.as_view(), name='admin-order-update'),
]