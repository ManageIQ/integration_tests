# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0015_auto_20150324_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='not_needed_anymore',
            field=models.BooleanField(
                default=False, help_text=b'Used for marking the appliance pool as being deleted'),
            preserve_default=True,
        ),
    ]
