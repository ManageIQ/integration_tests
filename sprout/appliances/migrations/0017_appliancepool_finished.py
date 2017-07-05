# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0016_appliancepool_not_needed_anymore'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='finished',
            field=models.BooleanField(
                default=False, help_text=b'Whether fulfillment has been met.'),
        ),
    ]
