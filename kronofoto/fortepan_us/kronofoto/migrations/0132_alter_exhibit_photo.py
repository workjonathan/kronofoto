# Generated by Django 4.2.13 on 2024-12-05 20:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0131_rename_fill_style_move_card_fill_style_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exhibit',
            name='photo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='kronofoto.photo'),
        ),
    ]
