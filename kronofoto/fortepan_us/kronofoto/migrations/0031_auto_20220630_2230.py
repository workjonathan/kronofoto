# Generated by Django 3.2.13 on 2022-06-30 22:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0030_auto_20220627_2037'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='photospherepair',
            options={'verbose_name': 'Photo position'},
        ),
        migrations.AlterField(
            model_name='photospherepair',
            name='photo',
            field=models.ForeignKey(help_text='Select a photo then click Save and Continue Editing to use the interactive tool', on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photo'),
        ),
    ]
