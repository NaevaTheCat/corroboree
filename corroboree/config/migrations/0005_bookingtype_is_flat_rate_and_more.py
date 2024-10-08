# Generated by Django 5.0.4 on 2024-09-10 03:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0004_alter_member_share_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingtype',
            name='is_flat_rate',
            field=models.BooleanField(default=False, help_text='If set, the fee for this booking is not multiplied by the number of rooms booked'),
        ),
        migrations.AlterField(
            model_name='bookingtype',
            name='is_full_week_only',
            field=models.BooleanField(default=False),
        ),
    ]
