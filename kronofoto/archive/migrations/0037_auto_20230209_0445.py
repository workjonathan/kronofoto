# Generated by Django 3.2.17 on 2023-02-09 04:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0036_alter_photo_year'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='prepublishphoto',
            name='photo',
        ),
        migrations.RemoveField(
            model_name='scannedphoto',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='scannedphoto',
            name='donor',
        ),
        migrations.DeleteModel(
            name='PhotoVote',
        ),
        migrations.DeleteModel(
            name='PrePublishPhoto',
        ),
        migrations.DeleteModel(
            name='ScannedPhoto',
        ),
    ]
