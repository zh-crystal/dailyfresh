# Create your views here.
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection

from utils.mixin import LoginRequiredMixin
from ..goods.models import GoodsSKU


# /cart/add
class CartAddView(View):
    """购物车记录添加"""

    def post(self, request):
        """购物车记录添加"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 2, 'errmsg': '数据不完整'})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数目出错'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        if count > sku.stock:
            return JsonResponse({'res': 5, 'errmsg': '商品库存不足'})
        conn.hset(cart_key, sku_id, count)
        total_count = conn.hlen(cart_key)
        return JsonResponse({'res': 0, 'message': '添加成功', 'total_count': total_count})


# /cart
class CartInfoView(LoginRequiredMixin):
    """购物车页面显示"""

    def get(self, request):
        """显示"""
        user = request.user
        conn = get_redis_connection('default')
        cart_key = "cart_%d" % user.id
        cart_dict = conn.hgetall(cart_key)
        skus = list()
        total_count, total_price = 0, 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            amount = sku.price * int(count)
            sku.amount = amount
            sku.count = count
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        context = {'skus': skus,
                   'total_count': total_count,
                   'total_price': total_price}
        return render(request, 'cart.html', context)


# /cart/update
class CartUpdateView(View):
    """购物车记录更新"""

    def post(self, request):
        """购物车记录更新"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'res': 2, 'errmsg': '数据不完整'})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '商品数目出错'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
        if count > sku.stock:
            return JsonResponse({'res': 5, 'errmsg': '商品库存不足'})
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hset(cart_key, sku_id, count)
        vals = conn.hvals(cart_key)
        total_count = 0
        for val in vals:
            total_count += int(val)
        return JsonResponse({'res': 0, 'message': '更新成功', 'total_count': total_count})


# /cart/delete
class CartDeleteView(View):
    """购物车记录删除"""

    def post(self, request):
        """购物车记录删除"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 2, 'errmsg': '无效的商品id'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hdel(cart_key, sku_id)
        vals = conn.hvals(cart_key)
        total_count = 0
        for val in vals:
            total_count += int(val)
        return JsonResponse({'res': 0, 'message': '删除成功', 'total_count': total_count})
