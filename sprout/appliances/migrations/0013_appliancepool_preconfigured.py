# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0012_template_preconfigured'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='preconfigured',
            field=models.BooleanField(
                default=True, help_text=b'Whether to provision preconfigured appliances'),
            preserve_default=True,
        ),
    ]
