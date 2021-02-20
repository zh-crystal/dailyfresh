# Register your models here.
from django.contrib import admin
from django.core.cache import cache

from celery_tasks.tasks import generate_static_index_html
from .models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner


class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """admin新增或更新表中的数据时调用"""
        super().save_model(request, obj, form, change)
        generate_static_index_html.delay()
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """admin删除表中的数据时调用"""
        super().delete_model(request, obj)
        generate_static_index_html.delay()
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class GoodsSKUAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
