# Generated by Django 4.2.11 on 2025-02-25 12:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0002_member_year_alter_member_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='member',
            unique_together={('account_number', 'year')},
        ),
    ]
