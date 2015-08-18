# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0021_userappliancequota'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='yum_update',
            field=models.BooleanField(default=False, help_text=b'Whether to update appliances.'),
        ),
    ]
