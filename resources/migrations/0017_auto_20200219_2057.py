# Generated by Django 2.2.10 on 2020-02-20 02:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0016_iabforeclosuresindexpage_body'),
    ]

    operations = [
        migrations.AlterField(
            model_name='iabaffordabilityindexpage',
            name='intro',
            field=models.CharField(max_length=250),
        ),
        migrations.AlterField(
            model_name='iabdemolitionsindexpage',
            name='intro',
            field=models.CharField(max_length=250),
        ),
        migrations.AlterField(
            model_name='iabforeclosuresindexpage',
            name='intro',
            field=models.CharField(max_length=250),
        ),
        migrations.AlterField(
            model_name='iabhousingindexpage',
            name='intro',
            field=models.CharField(max_length=250),
        ),
    ]
