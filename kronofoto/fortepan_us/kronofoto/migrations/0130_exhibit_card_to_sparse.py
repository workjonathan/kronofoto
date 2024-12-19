# Generated by Django 4.2.13 on 2024-12-03 17:15

from django.db import migrations

def photocard_to_card(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    PhotoCard = apps.get_model('kronofoto', 'PhotoCard')
    Card = apps.get_model('kronofoto', 'Card')
    for object in PhotoCard.objects.all():
        object.fill_style_move = object.fill_style
        object.card_type = object.alignment
        object.photo_move = object.photo
        object.save()


def card_to_photocard(apps, schema_editor):
    raise RuntimeError("""This is not written.
    In the event that this migration is needed, it should create records in the
    PhotoCard table with raw SQL for every Card where card_style is not TEXT_ONLY (0).
    """)

class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0129_card_card_type_card_fill_style_move_card_photo_move'),
    ]

    operations = [
        migrations.RunPython(photocard_to_card, card_to_photocard),
    ]
