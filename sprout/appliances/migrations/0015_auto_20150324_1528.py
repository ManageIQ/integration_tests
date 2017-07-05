# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0014_group_unconfigured_template_pool_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='description',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliancepool',
            name='description',
            field=models.TextField(blank=True),
            preserve_default=True,
        ),
    ]
