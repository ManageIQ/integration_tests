# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0013_appliancepool_preconfigured'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='unconfigured_template_pool_size',
            field=models.IntegerField(
                default=0,
                help_text=(
                    b'How many appliances to keep spinned for quick taking - unconfigured ones.')),
            preserve_default=True,
        ),
    ]
