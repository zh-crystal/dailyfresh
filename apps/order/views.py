# Create your views here.
from datetime import datetime

from alipay import AliPay
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import View
from django_redis import get_redis_connection

from utils.mixin import LoginRequiredMixin
from .models import OrderInfo, OrderGoods
from ..goods.models import GoodsSKU
from ..user.models import Address


# /order/place
class OrderPlaceView(LoginRequiredMixin):
    """提交订单页面"""

    @transaction.atomic
    def post(self, request):
        """显示"""
        user = request.user
        sku_ids = request.POST.getlist('sku_ids')
        if not sku_ids:
            return redirect(reverse('cart:show'))
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        skus = list()
        total_count, total_price = 0, 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price * int(count)
            total_count += int(count)
            total_price += amount
            sku.count = count
            sku.amount = amount
            skus.append(sku)
        transit_price = 10
        total_pay = total_price + transit_price
        addrs = Address.objects.filter(user=user)
        sku_ids = ','.join(sku_ids)
        context = {'skus': skus,
                   'total_count': total_count,
                   'total_price': total_price,
                   'transit_price': transit_price,
                   'total_pay': total_pay,
                   'addrs': addrs,
                   'sku_ids': sku_ids}
        return render(request, 'place_order.html', context)


# /order/commit
class OrderCommitView(View):
    """订单创建"""

    def post(self, request):
        """订单创建"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 2, 'errmsg': '数据不完整'})
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': '支付方式不支持'})
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 4, 'errmsg': '地址不可用'})
        save_id = transaction.savepoint()
        try:
            order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
            transit_price = 10
            total_count, total_price = 0, 0
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 5, 'errmsg': '商品不存在'})
                    count = conn.hget(cart_key, sku_id)
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                        sales=new_sales)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单冲突'})
                        continue
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount
                    break
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 8, 'errmsg': '下单失败'})
        transaction.savepoint_commit(save_id)
        conn.hdel(cart_key, *sku_ids)
        return JsonResponse({'res': 0, 'message': '创建成功'})


# /order/pay
class OrderPayView(View):
    """订单支付"""

    def post(self, request):
        """订单支付"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 2, 'errmsg': '无效的订单'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '订单错误，可能是支付方式暂不支持'})
        alipay = AliPay(
            appid=settings.ALIPAY['app_id'],
            app_notify_url=None,
            app_private_key_path=settings.ALIPAY['app_private_key_path'],
            alipay_public_key_path=settings.ALIPAY['alipay_public_key_path'],
            sign_type=settings.ALIPAY['sign_type'],
            debug=True
        )
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject='天天生鲜%s' % order_id,
            return_url=None,
            notify_url=None
        )
        pay_url = settings.ALIPAY['gateway_url'] + '?' + order_string
        return JsonResponse({'res': 0, 'pay_url': pay_url})


# /order/check
class CheckPayView(View):
    """查询支付结果"""

    def post(self, request):
        """查询支付结果"""
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 1, 'errmsg': '用户未登录'})
        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 2, 'errmsg': '无效的订单'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '订单错误'})
        alipay = AliPay(
            appid=settings.ALIPAY['app_id'],
            app_notify_url=None,
            app_private_key_path=settings.ALIPAY['app_private_key_path'],
            alipay_public_key_path=settings.ALIPAY['alipay_public_key_path'],
            sign_type=settings.ALIPAY['sign_type'],
            debug=True
        )
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                order.trade_no = response.get('trade_no')
                order.order_status = 4
                order.save()
                return JsonResponse({'res': 0, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                import time
                time.sleep(5)
                continue
            else:
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


# /order/comment
class CommentView(LoginRequiredMixin):
    """订单评论"""

    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            order_sku.amount = order_sku.count * order_sku.price
        order.order_skus = order_skus
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))
        total_count = request.POST.get("total_count")
        total_count = int(total_count)
        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = content
            order_goods.save()
        order.order_status = 5
        order.save()
        return redirect(reverse("user:order", kwargs={"page": 1}))
