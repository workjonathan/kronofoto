# Generated by Django 3.2.17 on 2023-06-19 01:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0058_alter_photo_photographer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='caption',
            field=models.TextField(blank=True, verbose_name='comment'),
        ),
    ]
