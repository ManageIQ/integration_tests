# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0019_auto_20150430_1546'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliance',
            name='lun_disk_connected',
            field=models.BooleanField(
                default=False, help_text=b'Whether the Direct LUN disk is connected. (RHEV Only)'),
        ),
    ]
