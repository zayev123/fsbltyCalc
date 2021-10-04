# Generated by Django 3.2.7 on 2021-10-04 17:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('feasibility_calculator', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='production',
            name='supervisor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='productions', to=settings.AUTH_USER_MODEL),
        ),
    ]
