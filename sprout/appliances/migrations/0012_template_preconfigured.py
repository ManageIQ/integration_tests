# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0011_auto_20150212_0945'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='preconfigured',
            field=models.BooleanField(default=True, help_text=b'Is prepared for immediate use?'),
            preserve_default=True,
        ),
    ]
