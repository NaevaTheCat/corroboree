# Generated by Django 5.0.4 on 2024-06-27 04:04

import django.core.validators
import django.db.models.deletion
import django.db.models.expressions
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_weeks_till_booking', models.IntegerField(default=26)),
                ('time_of_day_rollover', models.TimeField(help_text='What time of day to open bookings for the day max_weeks_till_booking from now')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('share_number', models.IntegerField(primary_key=True, serialize=False, validators=[django.core.validators.MaxValueValidator(50, message='Cannot exceed 50 shares'), django.core.validators.MinValueValidator(1, message='Share number is less than 1')])),
                ('first_name', models.CharField(max_length=128)),
                ('last_name', models.CharField(max_length=128)),
                ('contact_email', models.EmailField(max_length=254)),
                ('config', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.PROTECT, related_name='members', to='config.config')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FamilyMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=128)),
                ('last_name', models.CharField(max_length=128)),
                ('contact_email', models.EmailField(max_length=254)),
                ('primary_shareholder', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='family', to='config.member')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RoomType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('double_beds', models.IntegerField(validators=[django.core.validators.MaxValueValidator(2), django.core.validators.MinValueValidator(0)])),
                ('bunk_beds', models.IntegerField(validators=[django.core.validators.MaxValueValidator(4), django.core.validators.MinValueValidator(0)])),
                ('max_occupants', models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(django.db.models.expressions.CombinedExpression(models.F('double_beds'), '*', models.Value(2)), '+', models.F('bunk_beds')), output_field=models.IntegerField())),
                ('config', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='room_types', to='config.config')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('room_number', models.IntegerField(primary_key=True, serialize=False, validators=[django.core.validators.MaxValueValidator(9, 'Exceeds maximum rooms'), django.core.validators.MinValueValidator(1)])),
                ('config', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.PROTECT, related_name='rooms', to='config.config')),
                ('room_type', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.PROTECT, related_name='rooms', to='config.roomtype')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season_name', models.CharField(max_length=128)),
                ('max_monthly_room_weeks', models.IntegerField(blank=True, help_text='Leave blank for no limit', null=True)),
                ('start_month', models.IntegerField(choices=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], help_text='The season will begin at the first day of the selected month')),
                ('end_month', models.IntegerField(choices=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], help_text='The season will end at the end of the last day of the selected month')),
                ('season_is_peak', models.BooleanField()),
                ('config', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.PROTECT, related_name='seasons', to='config.config')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BookingType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking_type_name', models.CharField(max_length=128)),
                ('rate', models.DecimalField(decimal_places=2, max_digits=8)),
                ('is_full_week_only', models.BooleanField()),
                ('minimum_rooms', models.IntegerField(verbose_name='Minimum number of booked rooms')),
                ('priority_rank', models.IntegerField(choices=[(1, 'High'), (2, 'Medium'), (3, 'Low')], default=3, help_text='Priority booking takes when calculating costs when multiple kinds are valid.')),
                ('config', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.PROTECT, related_name='booking_types', to='config.config')),
                ('banned_rooms', modelcluster.fields.ParentalManyToManyField(blank=True, to='config.room')),
                ('season_active', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_types', to='config.season')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
