# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0022_appliancepool_yum_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='disabled',
            field=models.BooleanField(
                default=False, help_text=b'We can disable providers if we want.'),
        ),
    ]
