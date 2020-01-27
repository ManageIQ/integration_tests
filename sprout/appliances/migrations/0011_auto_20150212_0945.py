

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0010_appliance_power_state_changed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delayedprovisiontask',
            name='lease_time',
            field=models.IntegerField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='delayedprovisiontask',
            name='provider_to_avoid',
            field=models.ForeignKey(
                blank=True, to='appliances.Provider', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
