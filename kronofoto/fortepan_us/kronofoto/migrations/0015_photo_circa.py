# Generated by Django 2.2.10 on 2021-01-15 20:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0014_auto_20210111_2258'),
    ]

    operations = [
        migrations.AddField(
            model_name='photo',
            name='circa',
            field=models.BooleanField(default=False),
        ),
    ]
