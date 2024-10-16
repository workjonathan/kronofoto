# Generated by Django 4.2.13 on 2024-10-16 01:40

from django.db import migrations

def copytoarchivebase(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Archive = apps.get_model('kronofoto', 'Archive')
    ArchiveBase = apps.get_model('kronofoto', 'ArchiveBase')
    for archive in Archive.objects.using(db_alias).all():
        base = ArchiveBase.objects.using(db_alias).create(
            name=archive.name,
            slug=archive.slug,
            id=archive.id,
        )
        archive.archivebase_ptr = base
        archive.save()

def copytoarchive(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Archive = apps.get_model('kronofoto', 'Archive')
    ArchiveBase = apps.get_model('kronofoto', 'ArchiveBase')
    for archive in Archive.objects.using(db_alias).all():
        base = archive.archivebase_ptr
        archive.name = base.name
        archive.slug = base.slug
        archive.archivebase_ptr = None
        base.delete()
        archive.save()

class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0116_archivebase_followarchiverequest_alter_archive_name_and_more'),
    ]

    operations = [
        migrations.RunPython(copytoarchivebase, copytoarchive),
    ]
