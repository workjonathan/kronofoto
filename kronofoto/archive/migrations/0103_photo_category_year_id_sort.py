# Generated by Django 4.2.9 on 2024-02-15 23:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("archive", "0102_remove_photo_archive_pho_year_f1f0b8_idx_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="photo",
            index=models.Index(
                condition=models.Q(("is_published", True), ("year__isnull", False)),
                fields=["category", "year", "id"],
                name="category_year_id_sort",
            ),
        ),
    ]
