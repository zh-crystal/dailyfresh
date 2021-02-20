import os

from celery.task import task
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


@task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    subject = '天天生鲜账户验证'
    message = ''
    sender = settings.EMAIL_FROM
    recipliant = [to_email, ]
    html_message = '''
        <h1>%s, 欢迎您成为天天生鲜注册会员</h1>
        请点击下面链接激活您的账户<br/>
        <a href="http://%s:8000/user/active/%s">点击验证</a>
        ''' % (username, settings.SERVER_HOST, token)
    send_mail(subject, message, sender, recipliant, html_message=html_message)


@task
def generate_static_index_html():
    """生成首页静态页面"""
    # 1. 加载模板文件，返回模板对象
    temp = loader.get_template('static_index.html')
    # 2. 组织模板上下文
    types = GoodsType.objects.all()
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
    for type in types:
        type.title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        type.image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}
    # 3. 模板渲染
    static_index_html = temp.render(context)
    # 4. 生成首页静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)
