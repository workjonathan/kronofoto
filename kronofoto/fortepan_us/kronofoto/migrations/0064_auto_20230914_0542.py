# Generated by Django 3.2.21 on 2023-09-14 05:42

from django.db import migrations

def splitname(name):
    name = name.strip()
    if not name:
        return name
    names = name.split()
    if not len(names):
        return name
    return names[-1], ' '.join(names[:-1])

def set_new_photographer_field(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Donor = apps.get_model('kronofoto', 'Donor')
    Photo = apps.get_model('kronofoto', 'Photo')
    Submission = apps.get_model('kronofoto', 'Submission')
    for model in (Photo, Submission):
        photos_with_photographers = model.objects.exclude(photographer='')
        for photo in photos_with_photographers:
            last_name, first_name = splitname(photo.photographer)
            photographer, _ = Donor.objects.get_or_create(first_name=first_name, last_name=last_name, archive=photo.archive)
            photo.photographer_temp = photographer
            photo.save()


def set_old_photographer_field(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Donor = apps.get_model('kronofoto', 'Donor')
    Photo = apps.get_model('kronofoto', 'Photo')
    Submission = apps.get_model('kronofoto', 'Submission')
    for model in (Photo, Submission):
        photos_with_photographers = model.objects.exclude(photographer_temp__isnull=True)
        for photo in photos_with_photographers:
            photographer = photo.photographer_temp
            photo.photographer = " ".join([photographer.first_name, photographer.last_name])
            photo.photographer_temp = None
            photo.save()

class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0063_auto_20230914_0542'),
    ]

    operations = [
        migrations.RunPython(set_new_photographer_field, set_old_photographer_field),
    ]
