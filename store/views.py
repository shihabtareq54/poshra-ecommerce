import os
import uuid
import requests
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction 
from django.contrib.auth import authenticate
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Product, Category,Cart, CartItem, Order, OrderItem, ProductImage
from .serializers import (UserRegisterSerializer, 
                          ProductSerializer, CategorySerializer,
                          CartItemSerializer,CartSerializer, OrderSerializer
                          )
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Sum

# ==============================================================
# ১. অথেনটিকেশন API (BM-3)
# ==============================================================

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        '''data=request.data: আমরা ইউজারের পাঠানো সেই কাঁচা ডেটাগুলোকে 
        আমাদের আগে বানানো UserRegisterSerializer নামের যাচাইকারী মেশিনের 
        ভেতরে ঢুকিয়ে দিচ্ছি, যাতে সেগুলো ঠিক আছে কি না তা পরীক্ষা করা যায়।'''
        serializer = UserRegisterSerializer(data=request.data)


        '''সিরিয়ালাইজারের ভেতরে ডেটা দেওয়ার পর সাধারণত নিচের দুটি কাজ করতে হয়
        —প্রথমে ডেটা যাচাই করা (is_valid) এবং ঠিক থাকলে সেভ করা (save)'''

        if serializer.is_valid():     # ১. সব তথ্য ঠিক আছে কি না যাচাই করবে

            '''তথ্য ঠিক থাকলে save() ফাংশনটি আপনার সিরিয়ালাইজারের ভেতরে লেখা 
            create() মেথডটিকে চালু করে।
            ডেটাবেসে নতুন ইউজার তৈরি হওয়ার পর সেটি user নামের ভেরিয়েবলে জমা হয়।'''

            user = serializer.save()

            ''' 
	        এখন নতুন ইউজারের জন্য একটি গোপন অথেনটিকেশন টোকেন তৈরি করা দরকার। 
            এর ফলে রেজিস্ট্রেশন করার সাথে সাথেই ইউজার অ্যাপে অটো-লগইন হয়ে যায়।

	        get_or_create: এই ফাংশনটি একসাথে দুটি জিনিস ফেরত দেয়—প্রথমত আসল টোকেন
            অবজেক্ট (token), এবং দ্বিতীয়ত টোকেনটি নতুন তৈরি হলো নাকি আগে থেকেই ছিল তার 
            একটি সংকেত (True বা False)।

	        আন্ডারস্কোর (_) কী: Python-এ আন্ডারস্কোর (_) একটি প্রচলিত নিয়ম, যা দিয়ে বোঝানো 
            হয় যে দ্বিতীয় মানটি (True/False) আমাদের এখন কোনো কাজে লাগবে না, 
            তাই আমরা সেটি ফেলে দিচ্ছি বা উপেক্ষা করছি।'''

            token,_ = Token.objects.get_or_create(user=user)
            
            '''এবার আমরা নতুন ইউজারের জন্য তৈরি করা টোকেনটি JSON আকারে
            রেসপন্স হিসেবে পাঠিয়ে দিচ্ছি।'''
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        
        user = authenticate(
            username=request.data.get('username'),
            password=request.data.get('password')
        )

        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'is_staff': user.is_staff,   # <-- এখানে (সফল লগইনের ভেতরে) বসবে!
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_204_NO_CONTENT)









# ==============================================================
# ২. প্রোডাক্ট ক্যাটালগ, সার্চ, ফিল্টার ও পেজিনেশন API (BM-4)
# ==============================================================

'''ই কোডটি হলো Django REST Framework (DRF)-এর একটি রেডিমেড জেনেরিক ভিউ, 
যা ডেটাবেস থেকে সব ক্যাটাগরির তালিকা (List) একসাথে বের করে JSON আকারে দেখানোর 
জন্য তৈরি করা হয়েছে। আগে APIView ব্যবহার করলে আমাদের def get(self, request): 
লিখে ম্যানুয়ালি ডেটা আনতে হতো, কিন্তু generics.ListAPIView ব্যবহার করার ফলে 
মাত্র ৪ লাইনের কনফিগারেশনেই পুরো কাজটি স্বয়ংক্রিয়ভাবে হয়ে যায়।'''


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()  # টেবিলের ভেতরে থাকা সব ক্যাটাগরি তুলে আনা হচ্ছে

    '''
    ডেটাবেস থেকে আনা ক্যাটাগরিগুলোকে কোন সিরিয়ালাইজার দিয়ে JSON ফরম্যাটে
    রূপান্তর করা হবে, তা এখানে বলে দিতে হবে।
    '''

    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None  
    '''প্রজেক্টে যদি পেজিনেশন (Pagination) চালু থাকে (যেমন—প্রতি পেইজে ১০টি করে 
    আইটেম দেখানো), তবে এই লাইনটি ক্যাটাগরির জন্য সেই নিয়মটি বন্ধ করে দেয়। 
    এর ফলে সাইটে যতগুলো ক্যাটাগরি আছে, সবগুলো কোনো ভাগ ছাড়াই একসাথে চলে আসবে।'''


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all().order_by('-created_at')  # নতুন প্রোডাক্টগুলো আগে দেখানোর জন্য সাজানো হচ্ছে
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    '''
    filter_backends = (ফিল্টারিং ইঞ্জিনসমূহ)

    একটি লিস্টের মাধ্যমে Django-কে বলে দেওয়া হবে এই ভিউতে কোন কোন ধরনের খোঁজার 
    পদ্ধতি চালু থাকবে:

    DjangoFilterBackend: নির্দিষ্ট ফিল্ডের মান (যেমন ক্যাটাগরি আইডি বা দামের সীমা) মিলিয়ে 
    ডেটা ছাঁকনি করার জন্য।
    filters.SearchFilter: যেকোনো শব্দ বা টেক্সট লিখে সার্চ করার জন্য।
    filters.OrderingFilter: প্রোডাক্টগুলোকে ছোট থেকে বড় বা নতুন থেকে পুরাতন ক্রমে 
    সাজানোর জন্য।'''
    filter_backends = [DjangoFilterBackend, 
                       filters.SearchFilter, 
                       filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],           # ?category=1
        'price': ['gte', 'lte'],         # ['gte', 'lte'] লেখার মানে হলো Greater Than or Equal (>=) এবং Less Than or Equal (<=)!
        'brand': ['exact', 'icontains'],              # ?brand=Logitech
    }
    search_fields = ['name', 'description', 'brand']   # ?search=mouse
    ordering_fields = ['price', 'created_at'] # ?ordering=price (কম থেকে বেশি দাম)

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]









# ==============================================================
# ৩. শপিং কার্ট API (BM-5)
# ==============================================================

class CartView(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemCreateView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))

        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        product = generics.get_object_or_404(Product, id=product_id)

        # আগে থেকেই কার্টে এই প্রোডাক্ট আছে কি না চেক:
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product,
            defaults={'quantity': 0}
            )
        new_quantity = cart_item.quantity + quantity

        # Stock Guard: স্টকের চেয়ে বেশি অর্ডার আটকে দেওয়া
        if new_quantity > product.stock:
            return Response(
                {'error': 'Not enough stock available.'}, 
                status=status.HTTP_400_BAD_REQUEST
                )

        cart_item.quantity = new_quantity
        cart_item.save()
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Security: ইউজার যেন শুধু নিজের কার্টের আইটেমই এডিট/ডিলিট করতে পারে!
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_update(self, serializer):
        # পরিমাণ আপডেট (PATCH) করার সময়ও স্টক চেক:
        new_qty = serializer.validated_data.get('quantity', serializer.instance.quantity)
        if new_qty > serializer.instance.product.stock:
            
            raise ValidationError('Not enough stock available.')
        serializer.save()


    

    
# ==============================================================
# ৪. অর্ডার হিস্ট্রি, Atomic Checkout ও SSLCommerz (BM-6 & BM-7)
# ==============================================================

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        shipping_address = request.data.get('shipping_address')
        phone = request.data.get('phone')
        if not shipping_address or not phone:
            return Response(
                {"error": "Shipping address and phone number are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in cart.items.all():
            if item.quantity > item.product.stock:
                return Response(
                    {"error": f"Insufficient stock for {item.product.name}. Available: {item.product.stock}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        tran_id = f"POSHRA-{uuid.uuid4().hex[:10].upper()}"
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_price,
            transaction_id=tran_id,
            shipping_address=shipping_address,
            phone=phone
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_purchase=item.product.price
            )

        ssl_url = (
            "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            if settings.SSLCOMMERZ_IS_SANDBOX
            else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
        )
        base_url = request.build_absolute_uri('/').rstrip('/')

        post_data = {
            'store_id': settings.SSLCOMMERZ_STORE_ID,
            'store_passwd': settings.SSLCOMMERZ_STORE_PASS,
            'total_amount': str(order.total_amount),
            'currency': 'BDT',
            'tran_id': tran_id,
            'success_url': f"{base_url}/api/payment/success/",
            'fail_url': f"{base_url}/api/payment/fail/",
            'cancel_url': f"{base_url}/api/payment/cancel/",
            'cus_name': request.user.username,
            'cus_email': request.user.email or 'customer@poshra.com',
            'cus_add1': shipping_address,
            'cus_city': 'Dhaka',
            'cus_country': 'Bangladesh',
            'cus_phone': phone,
            'shipping_method': 'Courier',
            'ship_name': request.user.username,
            'ship_add1': shipping_address,
            'ship_city': 'Dhaka',
            'ship_postcode': '1230',
            'ship_country': 'Bangladesh',
            'product_name': f'Poshra Order #{order.id}',
            'product_category': 'Electronics',
            'product_profile': 'general',
        }

        ssl_response = requests.post(ssl_url, data=post_data, timeout=15).json()

        if ssl_response.get('status') == 'SUCCESS':
            return Response({
                "order_id": order.id,
                "transaction_id": tran_id,
                "payment_url": ssl_response.get('GatewayPageURL')
            }, status=status.HTTP_201_CREATED)
        else:
            raise Exception(f"SSLCommerz Error: {ssl_response.get('failedreason', 'Gateway init failed')}")


class PaymentSuccessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        tran_id = request.data.get('tran_id')
        val_id = request.data.get('val_id')
        frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500/frontend')

        order = generics.get_object_or_404(Order, transaction_id=tran_id)

        if order.payment_status != 'Paid':
            val_url = (
                "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
                if settings.SSLCOMMERZ_IS_SANDBOX
                else "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
            )
            params = {
                'val_id': val_id,
                'store_id': settings.SSLCOMMERZ_STORE_ID,
                'store_passwd': settings.SSLCOMMERZ_STORE_PASS,
                'format': 'json'
            }
            val_res = requests.get(val_url, params=params, timeout=15).json()

            if val_res.get('status') in ['VALID', 'VALIDATED']:
                order.payment_status = 'Paid'
                order.status = 'Processing'
                order.save()

                for item in order.items.all():
                    product = item.product
                    product.stock = max(0, product.stock - item.quantity)
                    product.save()

                CartItem.objects.filter(cart__user=order.user).delete()
            else:
                order.payment_status = 'Failed'
                order.save()
                return HttpResponse(f"""
                    <div style="font-family:Inter,sans-serif; text-align:center; padding:60px 20px;">
                        <h1 style="color:#dc2626;">Payment Verification Failed</h1>
                        <p>Could not verify your transaction ({tran_id}).</p>
                        <a href="{frontend_url}/cart.html" style="display:inline-block; margin-top:20px; padding:10px 20px; background:#081621; color:#fff; text-decoration:none; border-radius:6px;">Return to Cart</a>
                    </div>
                """)

        html_receipt = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Order Confirmed | POSHRA</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
        </head>
        <body style="margin:0; background:#f2f4f8; font-family:'Inter',sans-serif; display:flex; justify-content:center; align-items:center; min-height:100vh; padding:20px;">
            <div style="background:#ffffff; max-width:500px; width:100%; border-radius:12px; padding:36px; box-shadow:0 10px 30px rgba(0,0,0,0.08); text-align:center; border-top:6px solid #16a34a;">
                <div style="width:64px; height:64px; background:#dcfce7; color:#16a34a; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:16px;">✓</div>
                <h1 style="margin:0 0 8px; color:#111827; font-size:24px;">Order Confirmed! 🎉</h1>
                <p style="margin:0 0 24px; color:#6b7280; font-size:14px;">Thank you for shopping with <strong>পসরা (POSHRA)</strong>. Your payment has been verified.</p>

                <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:16px; text-align:left; font-size:13.5px; margin-bottom:24px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="color:#6b7280;">Order ID:</span>
                        <strong>#{order.id}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="color:#6b7280;">Transaction ID:</span>
                        <strong>{order.transaction_id}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span style="color:#6b7280;">Amount Paid:</span>
                        <strong style="color:#ef4a23;">৳ {order.total_amount}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#6b7280;">Status:</span>
                        <strong style="color:#16a34a;">{order.payment_status} ({order.status})</strong>
                    </div>
                </div>

                <div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap;">
                    <a href="{frontend_url}/orders.html" style="background:#081621; color:#fff; padding:11px 20px; border-radius:6px; text-decoration:none; font-weight:600; font-size:13.5px;">📦 View My Orders</a>
                    <a href="{frontend_url}/index.html" style="background:#ef4a23; color:#fff; padding:11px 20px; border-radius:6px; text-decoration:none; font-weight:600; font-size:13.5px;">Continue Shopping</a>
                </div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_receipt)


class PaymentFailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        tran_id = request.data.get('tran_id')
        frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500/frontend')
        Order.objects.filter(transaction_id=tran_id).update(payment_status='Failed')
        return HttpResponse(f"""
            <div style="font-family:Inter,sans-serif; text-align:center; padding:60px 20px; background:#f2f4f8; min-height:100vh;">
                <div style="background:#fff; max-width:440px; margin:0 auto; padding:32px; border-radius:10px; border-top:6px solid #dc2626;">
                    <h2 style="color:#dc2626;">Payment Failed ❌</h2>
                    <p style="color:#4b5563;">Your payment could not be completed. Please try again.</p>
                    <a href="{frontend_url}/checkout.html" style="display:inline-block; margin-top:16px; padding:10px 20px; background:#ef4a23; color:#fff; text-decoration:none; border-radius:6px; font-weight:600;">Try Again</a>
                </div>
            </div>
        """)


class PaymentCancelView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        tran_id = request.data.get('tran_id')
        frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:5500/frontend')
        Order.objects.filter(transaction_id=tran_id).update(payment_status='Cancelled', status='Cancelled')
        return HttpResponse(f"""
            <div style="font-family:Inter,sans-serif; text-align:center; padding:60px 20px; background:#f2f4f8; min-height:100vh;">
                <div style="background:#fff; max-width:440px; margin:0 auto; padding:32px; border-radius:10px; border-top:6px solid #d97706;">
                    <h2 style="color:#d97706;">Payment Cancelled</h2>
                    <p style="color:#4b5563;">You cancelled the payment process.</p>
                    <a href="{frontend_url}/cart.html" style="display:inline-block; margin-top:16px; padding:10px 20px; background:#081621; color:#fff; text-decoration:none; border-radius:6px; font-weight:600;">Return to Cart</a>
                </div>
            </div>
        """)




# ==============================================================
# ৫. ব্র্যান্ড লিস্ট ও সাদিয়ার Store Admin APIs (BM-9 & BM-10)
# ==============================================================

class BrandListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category_id = request.query_params.get('category')
        qs = Product.objects.all()
        if category_id:
            qs = qs.filter(category_id=category_id)
        brands = list(qs.values_list('brand', flat=True).distinct().order_by('brand'))
        return Response(brands)


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        revenue = Order.objects.filter(payment_status='Paid').aggregate(total=Sum('total_amount'))['total'] or 0
        return Response({
            'total_revenue': revenue,
            'total_orders': Order.objects.count(),
            'pending_orders': Order.objects.filter(status='Pending').count(),
            'total_products': Product.objects.count(),
            'low_stock_count': Product.objects.filter(stock__lte=5).count(),
        })


class AdminProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = None

    def perform_create(self, serializer):
        product = serializer.save()
        #একসাথে একাধিক ছবি আপলোড করার জন্য
        for img in self.request.FILES.getlist('gallery'):
            ProductImage.objects.create(product=product, image=img)


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]


class AdminCategoryCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    pagination_class = None


class AdminOrderListView(generics.ListAPIView):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None


class AdminOrderStatusUpdateView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]