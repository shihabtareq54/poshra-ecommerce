from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from .models import Category, Product, Cart, CartItem, Order


class PoshraQATestSuite(APITestCase):
    """
    পসরা (Poshra) ই-কমার্সের সম্পূর্ণ অটোমেটেড QA টেস্ট স্যুট:
    ১. গেস্ট ক্যাটালগ ও ব্র্যান্ড ফিল্টারিং টেস্ট
    ২. স্টক গার্ড (Negative Test)
    ৩. IDOR সিকিউরিটি (অন্যের কার্ট ডিলিট প্রতিরোধ)
    ৪. রোল-বেসড অ্যাক্সেস কন্ট্রোল (সাধারণ কাস্টমার যেন Admin API-তে ঢুকতে না পারে)
    ৫. Mocked SSLCommerz চেকআউট ও ভ্যালিডেশনের পর স্টক কমানো এবং কার্ট খালি হওয়া
    """

    def setUp(self):
        # ১. টেস্ট ক্রেতা (Customer) এবং স্টোর অ্যাডমিন (Staff) তৈরি
        self.customer = User.objects.create_user(username='nadia', password='password123', email='nadia@test.com')
        self.other_user = User.objects.create_user(username='rafiq', password='password123')
        self.admin_user = User.objects.create_user(username='sadia', password='password123', is_staff=True)

        self.customer_token = Token.objects.create(user=self.customer)
        self.other_token = Token.objects.create(user=self.other_user)
        self.admin_token = Token.objects.create(user=self.admin_user)

        # ২. ক্যাটাগরি ও প্রোডাক্ট তৈরি
        self.category = Category.objects.create(name='Gaming Mouse', slug='gaming-mouse')
        self.mouse = Product.objects.create(
            category=self.category,
            name='Logitech G102',
            brand='Logitech',
            slug='logitech-g102',
            description='8000 DPI Gaming Mouse',
            price=1850.00,
            stock=5
        )

    def test_01_guest_can_view_and_filter_products(self):
        """TC-01: লগইন ছাড়াই ভিজিটর প্রোডাক্ট দেখতে ও ব্র্যান্ড দিয়ে ফিল্টার করতে পারবে"""
        res = self.client.get('/api/products/?brand=Logitech')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'Logitech G102')

    def test_02_guest_cannot_access_cart(self):
        """TC-02 (Negative): লগইন ছাড়া কার্টে ঢুকতে চাইলে 401 Unauthorized দেবে"""
        res = self.client.get('/api/cart/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_03_stock_guard_blocks_excess_quantity(self):
        """TC-03 (Negative): স্টকের (5) চেয়ে বেশি (10) কার্টে যোগ করতে চাইলে 400 দিয়ে আটকাবে"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        res = self.client.post('/api/cart/items/', {'product': self.mouse.id, 'quantity': 10}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_04_idor_security_prevents_deleting_other_users_cart(self):
        """TC-04 (Security): রাফিক (other_user) যেন নাদিয়ার কার্ট আইটেম ডিলিট করতে না পারে"""
        cart = Cart.objects.create(user=self.customer)
        item = CartItem.objects.create(cart=cart, product=self.mouse, quantity=2)

        # এবার অন্য ইউজার (rafiq) দিয়ে নাদিয়ার আইটেম ডিলিট করার চেষ্টা
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        res = self.client.delete(f'/api/cart/items/{item.id}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(CartItem.objects.filter(id=item.id).exists())

    def test_05_non_admin_blocked_from_store_admin_api(self):
        """TC-05 (RBAC Security): সাধারণ ক্রেতা যেন Admin Stats API-তে ঢুকতে না পারে (403 Forbidden)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        res = self.client.get('/api/admin-panel/stats/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # কিন্তু সাদিয়া (is_staff=True) ঢুকতে পারবে (200 OK)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        res_admin = self.client.get('/api/admin-panel/stats/')
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)

    @patch('store.views.requests.get')
    @patch('store.views.requests.post')
    def test_06_sslcommerz_checkout_and_stock_deduction(self, mock_post, mock_get):
        """TC-06 (E2E Flow): কার্ট -> চেকআউট -> SSLCommerz পেমেন্ট ভ্যালিড হলে স্টক কমবে ও কার্ট খালি হবে"""
        # ১. নাদিয়ার কার্টে ২টি মাউস যোগ করছি (আগে স্টক ছিল 5)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        self.client.post('/api/cart/items/', {'product': self.mouse.id, 'quantity': 2}, format='json')

        # ২. SSLCommerz Session API Mock করছি
        mock_post.return_value = MagicMock(
            json=lambda: {'status': 'SUCCESS', 'GatewayPageURL': 'https://sandbox.sslcommerz.com/mock-pay'}
        )

        checkout_res = self.client.post('/api/orders/checkout/', {
            'shipping_address': 'Uttara, Dhaka',
            'phone': '01711000000'
        }, format='json')
        self.assertEqual(checkout_res.status_code, status.HTTP_201_CREATED)
        tran_id = checkout_res.data['transaction_id']

        # ৩. SSLCommerz Validation API Mock করছি
        mock_get.return_value = MagicMock(json=lambda: {'status': 'VALID'})
        pay_res = self.client.post('/api/payment/success/', {'tran_id': tran_id, 'val_id': 'MOCK_VAL_123'})
        self.assertEqual(pay_res.status_code, status.HTTP_200_OK)

        # ৪. চূড়ান্ত যাচাই: অর্ডার Paid হয়েছে, স্টক 5 -> 3 হয়েছে, এবং কার্ট খালি হয়েছে!
        order = Order.objects.get(transaction_id=tran_id)
        self.mouse.refresh_from_db()
        self.assertEqual(order.payment_status, 'Paid')
        self.assertEqual(order.status, 'Processing')
        self.assertEqual(self.mouse.stock, 3)
        self.assertEqual(CartItem.objects.filter(cart__user=self.customer).count(), 0)