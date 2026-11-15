from django.contrib.auth import authenticate
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Product, Category,Cart, CartItem
from .serializers import (UserRegisterSerializer, 
                          ProductSerializer, CategorySerializer,
                          CartItemSerializer,CartSerializer
                          )
from django_filters.rest_framework import DjangoFilterBackend

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
    }
    search_fields = ['name', 'description']   # ?search=mouse
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


    

    
