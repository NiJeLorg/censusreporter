# Generated by Django 2.2.10 on 2020-02-19 03:07

from django.db import migrations
import modelcluster.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0010_remove_informationforactioncategory_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='informationforactionpage',
            name='categories',
            field=modelcluster.fields.ParentalManyToManyField(blank=True, to='resources.InformationForActionCategory'),
        ),
    ]