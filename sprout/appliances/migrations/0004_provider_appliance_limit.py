

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0003_auto_20141218_1534'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='appliance_limit',
            field=models.IntegerField(
                help_text=b'Hard limit of how many appliances can run on this provider', null=True),
            preserve_default=True,
        ),
    ]
