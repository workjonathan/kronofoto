# Generated by Django 2.2.10 on 2020-06-10 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0002_wordcount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wordcount',
            name='count',
            field=models.FloatField(),
        ),
    ]
