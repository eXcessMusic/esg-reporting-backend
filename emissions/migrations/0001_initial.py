# Generated by Django 5.1 on 2024-08-27 12:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ReductionStrategy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('date', models.DateField()),
                ('total_emissions_cache', models.FloatField(null=True)),
                ('reduction_strategies', models.ManyToManyField(related_name='reports', to='emissions.reductionstrategy')),
            ],
            options={
                'unique_together': {('name', 'date')},
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('category', models.CharField(choices=[('TRANSPORT', 'Vehicles & other transportation means'), ('ENERGY', 'Energy'), ('IT', 'IT & Electronic Material'), ('FURNITURE', 'Furniture & Other Manufactured Goods'), ('TOOLS', 'Tools & Machinery')], max_length=20)),
                ('description', models.CharField(max_length=250)),
                ('method', models.CharField(choices=[('DISTANCE', 'Distance-based'), ('CONSUMPTION', 'Consumption-based'), ('FUEL', 'Fuel-based'), ('SPEND', 'Spend-based')], max_length=20)),
                ('emission_factor', models.FloatField(help_text='Emission factor (e.g., kg CO2e per unit)')),
                ('value', models.FloatField(help_text='Annual usage or distance')),
                ('value_unit', models.CharField(choices=[('km', 'Kilometers'), ('kWh', 'Kilowatt Hours'), ('L', 'Liters'), ('kg', 'Kilograms'), ('USD', 'US Dollars')], max_length=10)),
                ('quantity', models.PositiveIntegerField(default=1, help_text='Number of items (e.g., number of vehicles)')),
                ('lifetime', models.PositiveIntegerField(help_text='Lifetime in years')),
                ('acquisition_year', models.PositiveIntegerField()),
                ('uncertainty', models.FloatField(help_text='Uncertainty percentage (margin of error)')),
                ('year', models.PositiveIntegerField(blank=True, help_text="Specific year for this source's data. If set, emissions are only calculated for this year. If null, the source is considered active from acquisition_year to acquisition_year + lifetime.", null=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sources', to='emissions.report')),
            ],
            options={
                'unique_together': {('name', 'report', 'year')},
            },
        ),
        migrations.CreateModel(
            name='Modification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modification_type', models.CharField(choices=[('VALUE', 'Value Modification'), ('EF', 'Emission Factor Modification')], max_length=5)),
                ('value', models.FloatField(help_text='New value or ratio to apply')),
                ('order', models.PositiveIntegerField(help_text='Order of application within the strategy')),
                ('start_year', models.PositiveSmallIntegerField(help_text='Year when the modification starts')),
                ('end_year', models.PositiveSmallIntegerField(blank=True, help_text='Year when the modification ends (if applicable)', null=True)),
                ('is_progressive', models.BooleanField(default=False)),
                ('target_value', models.FloatField(blank=True, null=True)),
                ('calculation_year', models.PositiveSmallIntegerField(help_text='Specific year for which this modification is calculated')),
                ('reduction_strategy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modifications', to='emissions.reductionstrategy')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modifications', to='emissions.source')),
            ],
            options={
                'unique_together': {('reduction_strategy', 'source', 'calculation_year')},
            },
        ),
    ]
