# Generated by Django 2.2.10 on 2020-03-11 23:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0020_auto_20200309_2311'),
    ]

    operations = [
        migrations.AddField(
            model_name='scannedphoto',
            name='accepted',
            field=models.BooleanField(null=True),
        ),
    ]
