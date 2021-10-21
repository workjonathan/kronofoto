# Generated by Django 3.2.8 on 2021-10-06 21:26

import archive.models
import archive.storage
import django.contrib.gis.db.models.fields
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0024_auto_20210923_2008'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='location_bounds',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='photo',
            name='location_point',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='photo',
            name='original',
            field=models.ImageField(null=True, storage=archive.storage.OverwriteStorage(), upload_to=archive.models.get_original_path),
        ),
        migrations.AlterField(
            model_name='photo',
            name='year',
            field=models.SmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(limit_value=1800), django.core.validators.MaxValueValidator(limit_value=2021)]),
        ),
    ]