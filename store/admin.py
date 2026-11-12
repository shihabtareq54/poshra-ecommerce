from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Category, Product, Cart, CartItem, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('id', 'name', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # নাম লিখলেই slug অটো তৈরি হবে!
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'stock', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock')  # সাদিয়া লিস্ট থেকেই সরাসরি দাম ও স্টক এডিট করতে পারবেন!
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_purchase')


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('id', 'user__username', 'transaction_id', 'phone')
    list_editable = ('status',)  # লিস্ট থেকেই Pending -> Shipped -> Delivered করা যাবে!
    inlines = [OrderItemInline]


admin.site.register(Cart, ModelAdmin)
admin.site.register(CartItem, ModelAdmin)