# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Appliance',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'name',
                    models.CharField(
                        help_text=b"Appliance's name as it is in the provider.", max_length=64)),
                (
                    'ip_address',
                    models.CharField(
                        help_text=b"Appliance's IP address", max_length=45, null=True)),
                (
                    'datetime_leased',
                    models.DateTimeField(
                        help_text=b'When the appliance was leased', null=True)),
                (
                    'leased_until',
                    models.DateTimeField(
                        help_text=b'When does the appliance lease expire', null=True)),
                (
                    'status',
                    models.TextField(
                        default=b'Appliance inserted into the system.')),
                (
                    'status_changed',
                    models.DateTimeField(
                        auto_now_add=True)),
                (
                    'marked_for_deletion',
                    models.BooleanField(
                        default=False, help_text=b'Appliance is already being deleted.')),
                (
                    'power_state',
                    models.CharField(
                        default=b'unknown', help_text=b"Appliance's power state", max_length=32)),
                (
                    'ready',
                    models.BooleanField(
                        default=False,
                        help_text=b'Appliance has an IP address and web UI is online.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AppliancePool',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'total_count',
                    models.IntegerField(
                        help_text=b'How many appliances should be in this pool.')),
                (
                    'version',
                    models.CharField(
                        help_text=b'Appliance version', max_length=16, null=True)),
                (
                    'date',
                    models.DateField(
                        help_text=b'Appliance date.', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                (
                    'id',
                    models.CharField(
                        help_text=b'Group name as trackerbot says. (eg. upstream, downstream-53z,'
                        ' ...)',
                        max_length=32, serialize=False, primary_key=True)),
                (
                    'template_pool_size',
                    models.IntegerField(
                        default=0,
                        help_text=b'How many appliances to keep spinned for quick taking.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                (
                    'id',
                    models.CharField(
                        help_text=b"Provider's key in YAML.",
                        max_length=32, serialize=False, primary_key=True)),
                (
                    'working',
                    models.BooleanField(
                        default=False, help_text=b'Whether provider is available.')),
                (
                    'num_simultaneous_provisioning',
                    models.IntegerField(
                        default=5,
                        help_text=b'How many simultaneous background provisioning tasks can run'
                        ' on this provider.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                (
                    'version',
                    models.CharField(
                        help_text=b'Downstream version.', max_length=16, null=True)),
                (
                    'date',
                    models.DateField(
                        help_text=b'Template build date (original).')),
                (
                    'original_name',
                    models.CharField(
                        help_text=b"Template's original name.", max_length=64)),
                (
                    'name',
                    models.CharField(
                        help_text=b"Template's name as it resides on provider.", max_length=64)),
                (
                    'status',
                    models.TextField(
                        default=b'Template inserted into the system')),
                (
                    'status_changed',
                    models.DateTimeField(
                        auto_now_add=True)),
                (
                    'ready',
                    models.BooleanField(
                        default=False, help_text=b'Template is ready-to-be-used')),
                (
                    'exists',
                    models.BooleanField(
                        default=True, help_text=b'Template exists in the provider.')),
                (
                    'provider',
                    models.ForeignKey(
                        help_text=b'Where does this template reside', to='appliances.Provider',
                        on_delete=models.CASCADE)),
                (
                    'template_group',
                    models.ForeignKey(
                        help_text=b'Which group the template belongs to.', to='appliances.Group',
                        on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='appliancepool',
            name='group',
            field=models.ForeignKey(
                help_text=b'Group which is used to provision appliances.', to='appliances.Group',
                on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliancepool',
            name='owner',
            field=models.ForeignKey(
                help_text=b'User who owns the appliance pool', to=settings.AUTH_USER_MODEL,
                on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliance',
            name='appliance_pool',
            field=models.ForeignKey(
                to='appliances.AppliancePool',
                help_text=b'Which appliance pool this appliance belongs to.', null=True,
                on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='appliance',
            name='template',
            field=models.ForeignKey(
                help_text=b"Appliance's source template.", to='appliances.Template',
                on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
