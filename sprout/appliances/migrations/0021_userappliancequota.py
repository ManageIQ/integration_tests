# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('appliances', '0020_appliance_lun_disk_connected'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserApplianceQuota',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('per_pool_quota', models.IntegerField(null=True, blank=True)),
                ('total_pool_quota', models.IntegerField(null=True, blank=True)),
                ('total_vm_quota', models.IntegerField(null=True, blank=True)),
                ('user', models.OneToOneField(related_name='quotas', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
