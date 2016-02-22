# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0020_appliance_lun_disk_connected'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='delete_automation_script_name',
            field=models.TextField(
                help_text=b'Name of the script executed for automating the template deletion',
                null=True, blank=True),
        ),
        migrations.AddField(
            model_name='group',
            name='enable_delete_automation_script',
            field=models.BooleanField(
                default=False, help_text=b'Enable the template deletion script'),
        ),
        migrations.AddField(
            model_name='group',
            name='last_delete_script_exception',
            field=models.TextField(null=True, blank=True),
        ),
    ]
