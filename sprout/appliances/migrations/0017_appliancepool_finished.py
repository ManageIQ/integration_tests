

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0016_appliancepool_not_needed_anymore'),
    ]

    operations = [
        migrations.AddField(
            model_name='appliancepool',
            name='finished',
            field=models.BooleanField(
                default=False, help_text=b'Whether fulfillment has been met.'),
        ),
    ]
