# Generated by Django 4.2.9 on 2024-05-03 16:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0111_photo_archive_pho_archive_9df7f8_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archive",
            name="slug",
            field=models.SlugField(),
        ),
    ]
