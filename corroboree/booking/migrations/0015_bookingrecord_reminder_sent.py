# Generated by Django 5.0.4 on 2024-11-21 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0014_bookingpageusersummary_pay_text_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingrecord',
            name='reminder_sent',
            field=models.BooleanField(default=False),
        ),
    ]
