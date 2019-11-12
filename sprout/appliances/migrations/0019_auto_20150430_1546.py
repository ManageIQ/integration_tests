

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0018_mismatchversionmailer'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='template_obsolete_days',
            field=models.IntegerField(
                help_text=b"Templates older than X days won't be loaded into sprout",
                null=True, blank=True),
        ),
        migrations.AddField(
            model_name='group',
            name='template_obsolete_days_delete',
            field=models.BooleanField(
                default=False,
                help_text=b'If template_obsolete_days set, this will enable deletion of obsolete '
                b'templates using that metric. WARNING! Use with care. Best use for upstream '
                b'templates.'),
        ),
    ]
