# Generated by Django 3.2.22 on 2023-12-13 22:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0089_auto_20231213_0656'),
    ]

    operations = [
        migrations.AddField(
            model_name='photo',
            name='place',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='archive_photo_place', to='archive.place'),
        ),
        migrations.AddField(
            model_name='submission',
            name='place',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='archive_submission_place', to='archive.place'),
        ),
    ]