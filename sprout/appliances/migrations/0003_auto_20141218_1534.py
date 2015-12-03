# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0002_delayedprovisiontask'),
    ]

    operations = [
        migrations.AddField(
            model_name='delayedprovisiontask',
            name='provider_to_avoid',
            field=models.ForeignKey(to='appliances.Provider', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='delayedprovisiontask',
            name='lease_time',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
    ]
