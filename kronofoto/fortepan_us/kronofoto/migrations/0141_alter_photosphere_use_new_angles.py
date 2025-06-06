# Generated by Django 4.2.17 on 2025-03-25 19:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0140_photosphere_use_new_angles'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photosphere',
            name='use_new_angles',
            field=models.BooleanField(default=True, help_text='This option could fix photo sphere alignment issues. It should be enabled on all photo spheres. However, changing it may knock existing matches off.'),
        ),
    ]
