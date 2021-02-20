# Create your views here.
import re

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired

from celery_tasks.tasks import send_register_active_email
from utils.mixin import LoginRequiredMixin
from .models import User, Address
from ..goods.models import GoodsSKU
from ..order.models import OrderInfo, OrderGoods


# /user/register
class RegisterView(View):
    """注册"""

    def get(self, request):
        """显示注册页"""
        return render(request, 'register.html')

    def post(self, request):
        """处理注册业务"""
        # 1. 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        # 2. 校验数据，数据完整性和格式交由前端register.js
        ## 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})
        # 3. 业务处理
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600)
        token = serializer.dumps({'confirm': user.id}).decode()
        ## 发送账户激活邮件
        send_register_active_email.delay(email, username, token)
        return redirect(reverse('goods:index'))


# /user/active
class ActiveView(View):
    """激活"""

    def get(self, request, token):
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


# /user/login
class LoginView(View):
    """登录"""

    def get(self, request):
        """显示登录页"""
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """登录业务处理"""
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '用户名和密码未输入'})
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        elif user.is_active == 0:
            return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            login(request, user)
            next_url = request.GET.get('next', reverse('goods:index'))
            response = redirect(next_url)
            remember = request.POST.get('remember')
            if remember == 'on':
                response.set_cookie('username', username, max_age=24 * 3600)
            else:
                response.delete_cookie('username')
            return response


# /user/logout
class LogoutView(View):
    """登出"""

    def get(self, request):
        """登出"""
        logout(request)
        return redirect(reverse('goods:index'))


# /user
class UserInfoView(LoginRequiredMixin):
    """用户中心-信息页"""

    def get(self, request):
        """显示个人信息"""
        user = request.user
        address = Address.objects.get_default_address(user)
        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        sku_ids = con.lrange(history_key, 0, 4)
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        return render(request, 'user_center_info.html', {'page': 'user', 'address': address, 'goods_li': goods_li})


# /user/order
class UserOrderView(LoginRequiredMixin):
    """用户中心-订单页"""

    def get(self, request, page):
        """显示"""
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                order_sku.amount = order_sku.count * order_sku.price
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.total_pay = order.total_price + order.transit_price
            order.order_skus = order_skus
        paginator = Paginator(orders, 1)
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1
        order_page = paginator.page(page)
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}
        return render(request, 'user_center_order.html', context)


# /user/address
class AddressView(LoginRequiredMixin):
    """用户中心-信息页"""

    def get(self, request):
        """显示用户默认地址"""
        user = request.user
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        """添加地址"""
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '地址不完整'})
        if not re.match(r'^1[34578][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号码格式不正确'})
        user = request.user
        address = Address.objects.get_default_address(user)
        is_default = (address is None)
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        return redirect(reverse('user:address'))
