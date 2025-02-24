# Generated by Django 4.2.11 on 2025-02-22 19:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('account_number', models.CharField(max_length=50)),
                ('monthly_contributions', models.JSONField(default=dict)),
                ('annual_target', models.DecimalField(decimal_places=2, default=6000.0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
