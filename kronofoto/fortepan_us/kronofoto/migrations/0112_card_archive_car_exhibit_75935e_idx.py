# Generated by Django 4.2.9 on 2024-03-15 18:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kronofoto", "0111_doublephotocard_description2"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="card",
            index=models.Index(
                fields=["exhibit", "order"], name="archive_car_exhibit_75935e_idx"
            ),
        ),
    ]
