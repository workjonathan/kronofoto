# Generated by Django 3.2.21 on 2023-09-21 03:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kronofoto', '0072_remove_donor_users_starred_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photosphere',
            name='links',
            field=models.ManyToManyField(blank=True, related_name='_kronofoto_photosphere_links_+', to='kronofoto.PhotoSphere'),
        ),
    ]
