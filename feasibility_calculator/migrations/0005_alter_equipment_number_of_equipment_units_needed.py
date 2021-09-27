# Generated by Django 3.2.7 on 2021-09-27 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feasibility_calculator', '0004_alter_equipment_total_maintenance_down_time_fractions_per_hour'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipment',
            name='number_of_equipment_units_needed',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
