# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DelayedProvisionTask',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'lease_time',
                    models.IntegerField()),
                (
                    'pool',
                    models.ForeignKey(to='appliances.AppliancePool', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
