# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-10 16:37
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0026_template_parent_template'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='version',
            field=models.CharField(help_text=b'Downstream version.', max_length=32, null=True),
        ),
    ]
