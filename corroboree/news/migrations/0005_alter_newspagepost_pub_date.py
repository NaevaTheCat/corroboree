# Generated by Django 5.0.4 on 2024-10-30 06:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0004_alter_newspagepost_pub_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='newspagepost',
            name='pub_date',
            field=models.DateField(default=datetime.datetime(2024, 10, 30, 6, 39, 26, 853523, tzinfo=datetime.timezone.utc), verbose_name='Post date'),
        ),
    ]
