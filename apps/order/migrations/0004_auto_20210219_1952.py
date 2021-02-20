# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_auto_20210217_2123'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='trade_no',
            field=models.CharField(verbose_name='支付编号', max_length=128, default=''),
        ),
    ]
