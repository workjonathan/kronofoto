# Generated by Django 4.2.13 on 2024-11-25 04:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0135_ldid_serviceactor_delete_remotedonordata_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivebase',
            name='server_domain',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
