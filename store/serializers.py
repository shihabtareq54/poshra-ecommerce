from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image')


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    in_stock = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False)
    gallery = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'category', 'category_name', 'name', 'brand', 'slug',
            'description', 'price', 'stock', 'in_stock', 'image', 'gallery', 'created_at'
        )

    def get_in_stock(self, obj):
        return obj.stock > 0

    def create(self, validated_data):
        if not validated_data.get('slug'):
            validated_data['slug'] = f"{slugify(validated_data['name'])}-{uuid.uuid4().hex[:6]}"
        return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.ReadOnlyField(source='product.price')
    product_image = serializers.ImageField(source='product.image', read_only=True)
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_name', 'product_price', 'product_image', 'quantity', 'subtotal')


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_price', 'created_at')


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'price_at_purchase', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Order
        fields = (
            'id', 'customer_username', 'total_amount', 'status', 'payment_status',
            'transaction_id', 'shipping_address', 'phone', 'items', 'created_at'
        )