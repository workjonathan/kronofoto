# Generated by Django 3.2.17 on 2023-05-31 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0056_auto_20230503_0353'),
    ]

    operations = [
        migrations.AddField(
            model_name='donor',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
