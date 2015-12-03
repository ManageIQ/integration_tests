# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0008_appliance_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='provider',
            field=models.ForeignKey(
                blank=True, to='appliances.Provider',
                help_text=b'If requested, appliances can be on single provider.', null=True,
                on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
