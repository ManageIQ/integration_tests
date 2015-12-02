# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0017_appliancepool_finished'),
    ]

    operations = [
        migrations.CreateModel(
            name='MismatchVersionMailer',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('template_name', models.CharField(max_length=64)),
                ('supposed_version', models.CharField(max_length=32)),
                ('actual_version', models.CharField(max_length=32)),
                ('sent', models.BooleanField(default=False)),
                ('provider', models.ForeignKey(to='appliances.Provider', on_delete=models.CASCADE)),
            ],
        ),
    ]
