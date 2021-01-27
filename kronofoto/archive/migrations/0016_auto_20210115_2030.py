# Generated by Django 2.2.10 on 2021-01-15 20:30

from django.db import migrations

def copy_circa(apps, schema_editor):
    CSVRecord = apps.get_model('archive', 'CSVRecord')
    Photo = apps.get_model('archive', 'Photo')
    for record in CSVRecord.objects.filter(photo__isnull=False, circa=True):
        record.photo.circa = record.circa
        record.photo.save()


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0015_photo_circa'),
    ]

    operations = [
        migrations.RunPython(copy_circa),
    ]