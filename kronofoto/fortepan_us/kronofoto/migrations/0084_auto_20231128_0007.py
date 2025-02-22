# Generated by Django 3.2.22 on 2023-11-28 00:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0083_submission_terms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='is_published',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterIndexTogether(
            name='photo',
            index_together={('year', 'is_published')},
        ),
    ]
