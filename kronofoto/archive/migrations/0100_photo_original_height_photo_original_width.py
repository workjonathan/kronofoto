# Generated by Django 4.2.9 on 2024-02-08 06:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0099_remove_photo_h700_remove_photo_thumbnail"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="original_height",
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name="photo",
            name="original_width",
            field=models.IntegerField(default=0, editable=False),
        ),
    ]