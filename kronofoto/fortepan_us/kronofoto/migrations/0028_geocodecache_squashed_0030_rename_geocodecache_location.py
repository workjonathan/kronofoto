# Generated by Django 3.2.8 on 2022-06-22 00:38

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0027_auto_20220621_0259'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(unique=True)),
                ('location_point', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ('location_bounds', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
            ],
        ),
    ]
