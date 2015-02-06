# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0009_appliancepool_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='power_state_changed',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=True,
        ),
    ]
