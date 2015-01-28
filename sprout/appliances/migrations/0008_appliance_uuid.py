# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0007_provider_num_simultaneous_configuring'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='uuid',
            field=models.CharField(
                help_text=b'UUID of the machine', max_length=36, null=True, blank=True),
            preserve_default=True,
        ),
    ]
