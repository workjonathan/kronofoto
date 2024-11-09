# Generated by Django 4.2.9 on 2024-05-31 22:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("kronofoto", "0114_merge_20240530_2124"),
    ]

    operations = [
        migrations.AddField(
            model_name="exhibit",
            name="collection",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="kronofoto.collection",
            ),
        ),
    ]
