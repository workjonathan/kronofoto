# Generated by Django 3.2.21 on 2023-10-04 03:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('kronofoto', '0074_auto_20231004_0327'),
    ]

    operations = [
        migrations.AddField(
            model_name='archive',
            name='groups',
            field=models.ManyToManyField(through='kronofoto.ArchiveGroupPermission', to='auth.Group'),
        ),
    ]
