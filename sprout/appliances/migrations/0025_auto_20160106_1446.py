# Generated by Django 1.9.1 on 2016-01-06 14:46


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appliances', '0024_template_suggested_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='provider',
            field=models.ForeignKey(
                help_text=b'Where does this template reside',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='provider_templates',
                to='appliances.Provider'),
        ),
    ]
