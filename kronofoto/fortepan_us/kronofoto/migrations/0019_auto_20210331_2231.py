# Generated by Django 2.2.10 on 2021-03-31 22:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0018_auto_20210326_2116'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wordcount',
            name='field',
            field=models.CharField(choices=[('CA', 'Caption'), ('TA', 'Tag'), ('TE', 'Term')], db_index=True, max_length=2),
        ),
        migrations.AlterField(
            model_name='wordcount',
            name='word',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AlterIndexTogether(
            name='wordcount',
            index_together={('word', 'field')},
        ),
    ]
