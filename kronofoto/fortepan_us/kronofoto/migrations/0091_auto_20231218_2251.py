# Generated by Django 3.2.22 on 2023-12-18 22:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0090_auto_20231213_2223'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='photo',
            name='place',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='place',
        ),
        migrations.DeleteModel(
            name='Place',
        ),
    ]
