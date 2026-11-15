from rest_framework import serializers
from .models import Product, Category,Cart, CartItem, Order, OrderItem
from django.contrib.auth.models import User


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id',
                  'category',
                  'category_name', 
                  'name', 
                  'slug', 
                  'description', 
                  'price',
                  'stock', 
                  'in_stock',
                  'image',
                  'created_at']

    def get_in_stock(self, obj):
        return obj.stock > 0


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.ReadOnlyField(source='product.price')
    product_image = serializers.ImageField(source='product.image', read_only=True)
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'product_image', 'quantity', 'subtotal']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at' ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'price_at_purchase', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'total_amount', 'status', 'payment_status',
            'transaction_id', 'shipping_address', 'phone', 'items', 'created_at'
        )