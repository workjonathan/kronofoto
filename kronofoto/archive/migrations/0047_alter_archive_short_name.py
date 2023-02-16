# Generated by Django 3.2.17 on 2023-02-16 07:40

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0046_alter_archive_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archive',
            name='short_name',
            field=models.CharField(max_length=16, unique=True, validators=[django.core.validators.MinLengthValidator(1)]),
        ),
    ]
