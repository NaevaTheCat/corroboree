# Generated by Django 5.0.4 on 2024-05-01 03:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0006_remove_season_season_months_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='familymember',
            name='contact_email',
            field=models.EmailField(default='default@change.me', max_length=254),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='bookingtype',
            name='banned_rooms',
            field=models.ManyToManyField(blank=True, to='config.room'),
        ),
        migrations.AlterField(
            model_name='bookingtype',
            name='rate',
            field=models.DecimalField(decimal_places=2, max_digits=8),
        ),
    ]