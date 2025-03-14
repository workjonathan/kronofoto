# Generated by Django 3.2.17 on 2023-02-16 07:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0040_auto_20230210_0452'),
    ]

    operations = [
        migrations.CreateModel(
            name='Archive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('short_name', models.CharField(max_length=16, unique=True)),
                ('cms_root', models.CharField(max_length=16)),
                ('slug', models.SlugField(unique=True)),
            ],
        ),
    ]
