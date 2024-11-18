from datetime import datetime
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, F
from django.db.models.functions import Least
import numpy as np

class Report(models.Model):
    """
    The Report is the sum of all the emissions. It should be done once a year
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    date = models.DateField()
    reduction_strategies = models.ManyToManyField('ReductionStrategy', related_name='reports')
    total_emissions_cache = models.FloatField(null=True)  # New field for caching


    class Meta:
        unique_together = ['name', 'date']

    def __str__(self):
        return f"{self.name} - {self.date}"
    
    # Method to calculate total emissions for a report
    def total_emissions(self, year=None):
        """
        Calculate total emissions for the report, optionally for a specific year.
        """
        sources = self.sources.all()

        if year is None:
            return sources.aggregate(
                total=Sum(
                    F('emission_factor') * F('value') * F('quantity') *
                    Least(F('lifetime'), models.functions.ExtractYear(models.functions.Now()) - F('acquisition_year') + 1)
                )
            )['total'] or Decimal('0.00')

        return sources.filter(
            acquisition_year__lte=year,
            acquisition_year__gt=year - F('lifetime')
        ).aggregate(
            total=Sum(F('emission_factor') * F('value') * F('quantity'))
        )['total'] or Decimal('0.00')

    def compare_emissions(self, year1, year2):
        """
        Compare emissions between two years.
        Returns a dictionary with emission values and percentage change.
        """
        emissions1 = self.total_emissions(year1)
        emissions2 = self.total_emissions(year2)
        difference = emissions2 - emissions1
        percentage_change = ((difference / emissions1) * 100) if emissions1 else Decimal('0.00')
        return {
            'year1': year1,
            'year2': year2,
            'emissions1': emissions1,
            'emissions2': emissions2,
            'difference': difference,
            'percentage_change': percentage_change
        }
    
    def projected_total_emissions(self, year, reduction_strategies=None):
        """
        Calculate projected total emissions for a given year, optionally applying reduction strategies.
        Uses numpy for efficient calculations and prefetch_related for optimized database queries.
        """
        sources = self.sources.all().prefetch_related('modifications')
        
        # Create arrays for vectorized calculations
        emission_factors = np.array([source.emission_factor for source in sources])
        values = np.array([source.value for source in sources])
        quantities = np.array([source.quantity for source in sources])
        acquisition_years = np.array([source.acquisition_year for source in sources])
        lifetimes = np.array([source.lifetime for source in sources])

        # Calculate base emissions
        active_mask = (acquisition_years <= year) & (year < acquisition_years + lifetimes)
        base_emissions = np.where(active_mask, emission_factors * values * quantities, 0)

        if reduction_strategies:
            for strategy in reduction_strategies:
                modifications = strategy.modifications.filter(start_year__lte=year)
                for mod in modifications:
                    mod_mask = active_mask & (mod.source.id == np.array([s.id for s in sources]))
                    if mod.modification_type == 'VALUE':
                        base_emissions[mod_mask] *= float(mod.value)
                    elif mod.modification_type == 'EF':
                        base_emissions[mod_mask] *= (float(mod.value) / emission_factors[mod_mask])

        return Decimal(str(np.sum(base_emissions)))
    
    def update_total_emissions(self):
        """
        Update the cached total emissions value.
        """
        self.total_emissions_cache = self.total_emissions()
        self.save()

    def get_total_emissions(self):
        """
        Get the total emissions, using the cache if available.
        """
        if self.total_emissions_cache is None:
            self.update_total_emissions()
        return self.total_emissions_cache

class Source(models.Model):
    """
    A Source represents an emission source that generates greenhouse gases (GHG).
    It could be defined as source x emission_factor = total
    """
    CATEGORIES = [
        ('TRANSPORT', 'Vehicles & other transportation means'),
        ('ENERGY', 'Energy'),
        ('IT', 'IT & Electronic Material'),
        ('FURNITURE', 'Furniture & Other Manufactured Goods'),
        ('TOOLS', 'Tools & Machinery'),
        # Add other categories as needed
    ]
    METHODS = [
        ('DISTANCE', 'Distance-based'),
        ('CONSUMPTION', 'Consumption-based'),
        ('FUEL', 'Fuel-based'),
        ('SPEND', 'Spend-based'),
        # Add other methods as needed
    ]
    UNITS = [
        ('km', 'Kilometers'),
        ('kWh', 'Kilowatt Hours'),
        ('L', 'Liters'),
        ('kg', 'Kilograms'),
        ('USD', 'US Dollars'),
        # Add other units as needed
    ]
    
    name = models.CharField(max_length=100, unique=True, null=False, blank=False)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='sources')
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.CharField(max_length=250)
    method = models.CharField(max_length=20, choices=METHODS)
    emission_factor = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        help_text="Emission factor (e.g., kg CO2e per unit)"
    )
    value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Annual usage or distance for a single unit"
    )
    value_unit = models.CharField(max_length=10, choices=UNITS)
    quantity = models.PositiveIntegerField(
        help_text="Number of items (e.g., number of vehicles)"
    )
    lifetime = models.PositiveIntegerField(help_text="Lifetime in years")
    acquisition_year = models.PositiveIntegerField()
    uncertainty = models.FloatField(help_text="Uncertainty percentage (margin of error)")
    # The 'year' field allows for year-specific source data without creating duplicate Source instances.
    # This approach reduces database bloat and simplifies queries while maintaining yearly granularity when needed.
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Specific year for this source's data. If set, emissions are only calculated for this year. "
                    "If null, the source is considered active from acquisition_year to acquisition_year + lifetime."
    )

    class Meta:
        unique_together = ['name', 'report', 'year']

    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        if self.value <= Decimal('0'):
            raise ValidationError({'value': 'Value must be greater than zero.'})
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be greater than zero.'})
        if self.year and (self.year < self.acquisition_year or self.year >= self.acquisition_year + self.lifetime):
            raise ValidationError({'year': 'Year must be within the source\'s lifetime.'})
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def calculate_emission_for_year(self, year):
        """
        Calculate the emission for a specific year.
        Returns 0 if the source is not active in the given year.
        """
        if self.year and self.year != year:
            return Decimal('0.00')
        if year < self.acquisition_year or year >= self.acquisition_year + self.lifetime:
            return Decimal('0.00')
        return self.annual_emission

    @property
    def total_emission(self):
        """
        Calculate the total emission over the lifetime of the source.
        Considers the current year and caps the calculation at the source's lifetime.
        """
        from django.utils import timezone
        current_year = timezone.now().year
        years_active = max(0, min(current_year - self.acquisition_year + 1, self.lifetime))
        return self.emission_factor * self.value * self.quantity * years_active

    @property
    def annual_emission(self):
        """
        Calculate the annual emission for this source.
        """
        return self.emission_factor * self.value * self.quantity

class ReductionStrategy(models.Model):
    """
    A reduction strategy for reducing emissions.
    Can be associated with multiple reports and contain multiple modifications.
    """
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Modification(models.Model):
    """
    A modification applied to a source as part of a reduction strategy.
    Can be either a value modification or an emission factor modification.
    """
    MODIFICATION_TYPES = [
        ('VALUE', 'Value Modification'),
        ('EF', 'Emission Factor Modification'),
    ]

    reduction_strategy = models.ForeignKey(ReductionStrategy, on_delete=models.CASCADE, related_name='modifications')
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='modifications')
    modification_type = models.CharField(max_length=5, choices=MODIFICATION_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=4, help_text="New value or ratio to apply")
    order = models.PositiveIntegerField(help_text="Order of application within the strategy")
    start_year = models.PositiveSmallIntegerField(help_text="Year when the modification starts")
    end_year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Year when the modification ends (if applicable)")
    is_progressive = models.BooleanField(default=False)
    target_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # ---- Fields that were previously in ModifiedEmission ----
    calculation_year = models.PositiveSmallIntegerField(
        help_text="Specific year for which this modification is calculated",
        default=datetime.now().year
        )
    # Calculated fields now so commenting these just in case I need to time travel 😅
    """ modified_value = models.FloatField(help_text="Modified emission value for this year")
    modified_emission_factor = models.FloatField(help_text="Modified emission factor for this year")
    total_modified_emission = models.FloatField(help_text="Total modified emission for this year") """

    class Meta:
        unique_together = ('reduction_strategy', 'source', 'start_year', 'order')
        ordering = ['start_year', 'order']

    def __str__(self):
        return f"Modification for {self.source.name} in {self.calculation_year}"

    def save(self, *args, **kwargs):
        """
        Custom save method to automatically set the order if not provided.
        """
        if not self.order:
            last_order = Modification.objects.filter(
                reduction_strategy=self.reduction_strategy,
                source=self.source,
                start_year=self.start_year
            ).aggregate(models.Max('order'))['order__max'] or 0
            self.order = last_order + 1
        super().save(*args, **kwargs)

    def calculate_modified_emission(self, base_emission=None):
        """
        Calculate the modified emission for this modification.
        Handles both progressive and non-progressive modifications.
        :param base_emission: The base emission value to modify. If None, use the source's emission for the year.
        :return: The modified emission value
        """
        if base_emission is None:
            base_emission = self.source.calculate_emission_for_year(self.calculation_year)

        if self.modification_type == 'VALUE':
            if self.is_progressive:
                total_years = self.end_year - self.start_year + 1
                years_passed = min(self.calculation_year - self.start_year + 1, total_years)
                progress = Decimal(years_passed) / Decimal(total_years)
                current_value = self.source.value + (self.target_value - self.source.value) * progress
                return base_emission * (current_value / self.source.value)
            else:
                return base_emission * self.value
        elif self.modification_type == 'EF':
            return (base_emission / self.source.emission_factor) * self.value
        else:
            raise ValidationError(f"Unknown modification type: {self.modification_type}")

    def get_modified_emission(self):
        """
        Get the modified emission value, calculating it if necessary.
        Uses caching to avoid recalculation.
        """
        if not hasattr(self, '_modified_emission'):
            self._modified_emission = self.calculate_modified_emission()
        return self._modified_emission