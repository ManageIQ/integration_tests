

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0004_provider_appliance_limit'),
    ]

    operations = [
        migrations.AddField(
            model_name='template',
            name='usable',
            field=models.BooleanField(default=False, help_text=b'Template is marked as usable'),
            preserve_default=True,
        ),
    ]
