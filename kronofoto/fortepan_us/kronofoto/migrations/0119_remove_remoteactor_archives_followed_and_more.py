# Generated by Django 4.2.13 on 2024-10-16 02:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0118_remove_archive_archive_slug_idx_remove_archive_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='remoteactor',
            name='archives_followed',
        ),
        migrations.RemoveField(
            model_name='remoteactor',
            name='requested_archive_follows',
        ),
    ]
