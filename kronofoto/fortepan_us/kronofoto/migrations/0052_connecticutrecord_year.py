# Generated by Django 3.2.17 on 2023-03-09 04:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0051_auto_20230309_0439'),
    ]

    operations = [
        migrations.AddField(
            model_name='connecticutrecord',
            name='year',
            field=models.TextField(default=0),
            preserve_default=False,
        ),
    ]
