# Generated by Django 3.2.14 on 2022-07-29 22:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0032_auto_20220729_2222'),
    ]

    operations = [
        migrations.RenameField(
            model_name='photosphere',
            old_name='name',
            new_name='title',
        ),
    ]
