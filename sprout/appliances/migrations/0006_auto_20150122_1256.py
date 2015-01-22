# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0005_template_usable'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliancepool',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='delayedprovisiontask',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='group',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='provider',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='template',
            name='object_meta_data',
            field=models.TextField(default=b'{}\n'),
            preserve_default=True,
        ),
    ]
