# Generated by Django 2.2.10 on 2020-03-09 22:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0017_photovote'),
    ]

    operations = [
        migrations.AddField(
            model_name='photovote',
            name='infavor',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
