# Generated by Django 2.2.10 on 2020-08-05 23:12

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kronofoto', '0003_auto_20200610_2212'),
    ]

    operations = [
        migrations.AddField(
            model_name='phototag',
            name='creator',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
    ]
