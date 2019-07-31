# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0006_auto_20150122_1256'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='num_simultaneous_configuring',
            field=models.IntegerField(
                default=1,
                help_text=b'How many simultaneous template configuring tasks can run on this'
                ' provider.'),
            preserve_default=True,
        ),
    ]
