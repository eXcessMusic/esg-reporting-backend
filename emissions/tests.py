from datetime import datetime
import timeit
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from emissions.models import Report, Source, ReductionStrategy, Modification
from emissions.views import calculate_total_reduction
from django.db.models.signals import post_save, post_delete
import logging
from decimal import Decimal
from emissions.views import calculate_emissions_for_years, apply_modifications, calculate_total_reduction
import numpy as np

logger = logging.getLogger(__name__)

# ——————————————————————————————— Performance tests ————————————————————————————
class PerformanceTestCase(TestCase):
    def setUp(self):
        # Create test data
        self.report = Report.objects.create(name="Test Report", date=datetime.now().date())
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            description="Test description",
            method="DISTANCE",
            emission_factor=0.5,
            value=1000,
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5,
            year=None  # Adding this line to take into account the new year field added in v1.1
        )
        self.strategy = ReductionStrategy.objects.create(name="Test Strategy")
        self.modification = Modification.objects.create(
            reduction_strategy=self.strategy,
            source=self.source,
            modification_type="VALUE",
            value=0.9,
            start_year=2022
        )

    def test_calculate_emissions_performance(self):
        def run_calculation():
            return calculate_emissions_for_years(self.source, 2020, 2030)
        
        time = timeit.timeit(run_calculation, number=1000)
        print(f"Time to calculate emissions for years: {time:.6f} seconds")

    def test_apply_modifications_performance(self):
        def run_apply_modifications():
            emissions = np.array([100.0] * 11)  # 11 years from 2020 to 2030
            years = np.arange(2020, 2031)
            return apply_modifications(emissions, self.source, [self.modification], years)
        
        time = timeit.timeit(run_apply_modifications, number=1000)
        print(f"Time to apply modifications: {time:.6f} seconds")

    def test_calculate_total_reduction_performance(self):
        def run_total_reduction():
            return calculate_total_reduction(self.strategy, 2020, 2030)
        
        time = timeit.timeit(run_total_reduction, number=100)
        print(f"Time to calculate total reduction: {time:.6f} seconds")

# To run the tests:
# python manage.py test emissions.tests.PerformanceTestCase

# ——————————————————————————————— Unit tests ————————————————————————————————————
class SourceModelTest(TestCase):
    '''
    Test cases for the Source model.
    '''

    def setUp(self):
        '''
        Set up test data for the Source model tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            description="Test description",
            method="DISTANCE",
            emission_factor=0.1,
            value=1000,
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5,
            year=None  # Adding this line to take into account the new year field added in v1.1
        )

    def test_source_creation(self):
        '''
        Test that a Source object is created correctly.
        '''
        self.assertEqual(self.source.name, "Test Source")
        self.assertEqual(self.source.category, "TRANSPORT")
        self.assertEqual(self.source.emission_factor, 0.1)

    def test_year_specific_source(self):
        '''
        Test the behavior of a year-specific source.
        '''
        year_specific_source = Source.objects.create(
            name="Year Specific Source",
            report=self.report,
            category="ENERGY",
            description="Year specific source",
            method="CONSUMPTION",
            emission_factor=1,
            value=100,
            value_unit="kWh",
            quantity=1,
            lifetime=10,
            acquisition_year=2020,
            year=2022,  # Set the year field
            uncertainty=3
        )
        self.assertEqual(year_specific_source.calculate_emission_for_year(2022), 100.0)
        self.assertEqual(year_specific_source.calculate_emission_for_year(2025), 0)

    def test_total_emission_calculation(self):
        '''
        Test the total emission calculation for a source.
        '''
        current_year = datetime.now().year
        years_active = min(current_year - self.source.acquisition_year + 1, self.source.lifetime)
        expected_total_emission = self.source.emission_factor * self.source.value * self.source.quantity * years_active

        # Print debug information
        print(f"Source details: emission_factor={self.source.emission_factor}, value={self.source.value}, "
            f"quantity={self.source.quantity}, lifetime={self.source.lifetime}, "
            f"acquisition_year={self.source.acquisition_year}")
        print(f"Current year: {current_year}")
        print(f"Years active: {years_active}")
        print(f"Calculated total emission: {self.source.total_emission}")
        print(f"Expected total emission: {expected_total_emission}")

        self.assertAlmostEqual(self.source.total_emission, expected_total_emission, places=2)

    def test_str_representation(self):
        '''
        Test the string representation of a Source object.
        '''
        self.assertEqual(str(self.source), "Test Source")

class ProjectionViewSetTest(APITestCase):
    '''
    Test cases for the ProjectionViewSet.
    '''

    def setUp(self):
        '''
        Set up test data for the ProjectionViewSet tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            description="Test description",
            method="DISTANCE",
            emission_factor=Decimal('0.1'),
            value=Decimal('1000'),
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )
        self.reduction_strategy = ReductionStrategy.objects.create(name="Test Strategy")
        self.report.reduction_strategies.add(self.reduction_strategy)
        self.modification = Modification.objects.create(
            reduction_strategy=self.reduction_strategy,
            source=self.source,
            modification_type="VALUE",
            value=Decimal('0.9'),
            order=1,
            start_year=2024,
            end_year=None,
            is_progressive=False,
            target_value=None
        )

    def test_project_modifications(self):
        '''
        Test the projection of modifications.
        '''
        # 1. Send POST request
        url = reverse('projection-project-modifications')
        data = {
            "source_id": self.source.id,
            "modification_ids": [self.modification.id],
            "start_year": 2023,
            "end_year": 2075  # Test with a year beyond the 50-year limit
        }
        response = self.client.post(url, data, format='json')

        # 2. Check response and verify projections
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('projections', response.data)
        self.assertEqual(response.data['end_year'], 2073)  # Should be capped at 50 years from start

        projections = response.data['projections']
        print(f"Projected emissions: {projections}")  # For debugging

        self.assertIn('2023', projections)
        self.assertAlmostEqual(Decimal(projections['2023']), Decimal('20.0'), places=2)  # Base emission
        self.assertAlmostEqual(Decimal(projections['2024']), Decimal('18.0'), places=2)  # 10% reduction applied
        self.assertAlmostEqual(Decimal(projections['2025']), Decimal('18.0'), places=2)  # Should maintain the reduction
        self.assertAlmostEqual(Decimal(projections['2026']), Decimal('18.0'), places=2)  # Should maintain the reduction
        self.assertAlmostEqual(Decimal(projections['2027']), Decimal('18.0'), places=2)  # Still within lifetime
        self.assertAlmostEqual(Decimal(projections['2028']), Decimal('0.0'), places=2)   # Beyond lifetime, should be 0

        # Add a print statement to see the actual projections
        print(f"Projected emissions: {projections}")

    def test_progressive_modification(self):
        '''
        Test the projection of emissions with a progressive modification.
        This test creates a progressive modification, sends a request to calculate
        projections, and verifies the projected emissions for each year.
        '''
        # 1. Create progressive modification
        progressive_mod = Modification.objects.create(
            reduction_strategy=self.reduction_strategy,
            source=self.source,
            modification_type="VALUE",
            value=Decimal('1.0'),
            start_year=2024,
            end_year=2026,
            is_progressive=True,
            target_value=Decimal('2000')  # Double the original value
        )

        # 2. Send POST request and check response
        url = reverse('projection-project-modifications')
        data = {
            "source_id": self.source.id,
            "modification_ids": [progressive_mod.id],
            "start_year": 2023,
            "end_year": 2027
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Verify projected emissions
        projections = response.data['projections']
        expected_projections = {
            '2023': Decimal('20.00'),  # Base emission
            '2024': Decimal('26.67'),  # 1/3 increase
            '2025': Decimal('33.33'),  # 2/3 increase
            '2026': Decimal('40.00'),  # Full increase
            '2027': Decimal('40.00'),  # Stays at full increase
        }

        for year, expected in expected_projections.items():
            self.assertAlmostEqual(Decimal(projections[year]), expected, places=2)

class ReportModelTests(TestCase):
    '''
    Test cases for the Report model.
    '''

    def setUp(self):
        '''
        Set up test data for the Report model tests.
        '''
        self.report = Report.objects.create(name="Test Report", date=datetime.now().date())
        self.source1 = Source.objects.create(
            name="Source 1",
            report=self.report,
            category="TRANSPORT",
            description="Test source 1",
            method="DISTANCE",
            emission_factor=0.1,
            value=1000,
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2020,
            uncertainty=5
        )
        self.source2 = Source.objects.create(
            name="Source 2",
            report=self.report,
            category="ENERGY",
            description="Test source 2",
            method="CONSUMPTION",
            emission_factor=0.5,
            value=500,
            value_unit="kWh",
            quantity=1,
            lifetime=10,
            acquisition_year=2022,
            uncertainty=3
        )
        # Add multiple reduction strategies on the same report
        self.strategy1 = ReductionStrategy.objects.create(name="Strategy 1")
        self.strategy2 = ReductionStrategy.objects.create(name="Strategy 2")
        self.report.reduction_strategies.add(self.strategy1, self.strategy2)

    def test_total_emissions(self):
        '''
        Test the calculation of total emissions for a report.
        '''
        current_year = datetime.now().year
        print(f"Current year: {current_year}")

        # Test total emissions for all sources
        total = self.report.total_emissions()

        # Calculate expected total based on the current implementation
        source1_years_active = min(current_year - self.source1.acquisition_year + 1, self.source1.lifetime)
        source2_years_active = min(current_year - self.source2.acquisition_year + 1, self.source2.lifetime)

        expected_total = (self.source1.emission_factor * self.source1.value * self.source1.quantity * source1_years_active +
                        self.source2.emission_factor * self.source2.value * self.source2.quantity * source2_years_active)

        print(f"Source 1: emission_factor={self.source1.emission_factor}, value={self.source1.value}, "
            f"quantity={self.source1.quantity}, lifetime={self.source1.lifetime}, "
            f"acquisition_year={self.source1.acquisition_year}, years_active={source1_years_active}")
        print(f"Source 2: emission_factor={self.source2.emission_factor}, value={self.source2.value}, "
            f"quantity={self.source2.quantity}, lifetime={self.source2.lifetime}, "
            f"acquisition_year={self.source2.acquisition_year}, years_active={source2_years_active}")
        print(f"Total emissions: {total}")
        print(f"Expected total: {expected_total}")

        for source in self.report.sources.all():
            print(f"Source {source.name} total emission: {source.total_emission}")

        self.assertAlmostEqual(total, expected_total, places=2)

        # Test total emissions for a specific year
        test_year = 2021
        total_2021 = self.report.total_emissions(test_year)
        expected_total_2021 = self.source1.emission_factor * self.source1.value * self.source1.quantity
        print(f"Total emissions for {test_year}: {total_2021}")
        print(f"Expected total for {test_year}: {expected_total_2021}")
        self.assertAlmostEqual(total_2021, expected_total_2021, places=2)

    def test_compare_emissions(self):
        '''
        Test the comparison of emissions between two years.
        '''
        comparison = self.report.compare_emissions(2021, 2023)
        self.assertEqual(comparison['year1'], 2021)
        self.assertEqual(comparison['year2'], 2023)
        self.assertAlmostEqual(comparison['emissions1'], 0.1 * 1000 * 1, places=2)
        self.assertAlmostEqual(comparison['emissions2'], (0.1 * 1000 * 1) + (0.5 * 500 * 1), places=2)
        self.assertAlmostEqual(comparison['difference'], 0.5 * 500 * 1, places=2)
        self.assertAlmostEqual(comparison['percentage_change'], 250, places=2)

    def test_multiple_reduction_strategies(self):
        '''
        Test that multiple reduction strategies can be added to a report.
        '''
        self.assertEqual(self.report.reduction_strategies.count(), 2)
        self.assertIn(self.strategy1, self.report.reduction_strategies.all())
        self.assertIn(self.strategy2, self.report.reduction_strategies.all())

    def test_total_emissions_cache_update(self):
        '''
        Test that the total emissions cache is updated correctly when a source is modified.
        '''
        initial_total = self.report.get_total_emissions()
        print(f"Initial total emissions: {initial_total}")

        # Modify a source
        self.source1.value = 2000
        self.source1.save()

        # Check that the cache is updated
        self.report.update_total_emissions()
        updated_total = self.report.get_total_emissions()

        # Calculate expected updated total based on current model logic
        current_year = datetime.now().year
        years_active_source1 = min(current_year - self.source1.acquisition_year + 1, self.source1.lifetime)
        years_active_source2 = min(current_year - self.source2.acquisition_year + 1, self.source2.lifetime)

        expected_updated_total = (self.source1.emission_factor * 2000 * self.source1.quantity * years_active_source1) + \
                                (self.source2.emission_factor * self.source2.value * self.source2.quantity * years_active_source2)

        print(f"Source 1: emission_factor={self.source1.emission_factor}, value=2000, "
            f"quantity={self.source1.quantity}, lifetime={self.source1.lifetime}, "
            f"acquisition_year={self.source1.acquisition_year}, years_active={years_active_source1}")
        print(f"Source 2: emission_factor={self.source2.emission_factor}, value={self.source2.value}, "
            f"quantity={self.source2.quantity}, lifetime={self.source2.lifetime}, "
            f"acquisition_year={self.source2.acquisition_year}, years_active={years_active_source2}")
        print(f"Current year: {current_year}")
        print(f"Updated total emissions: {updated_total}")
        print(f"Expected updated total: {expected_updated_total}")

        self.assertAlmostEqual(updated_total, expected_updated_total, places=2)

class SignalTests(TestCase):
    '''
    Test cases for signal handlers related to emissions calculations.
    '''

    def setUp(self):
        '''
        Set up test data for the signal tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            emission_factor=0.1,
            value=1000,
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )

    def test_update_report_emissions_on_source_save(self):
        '''
        Test that report emissions are updated when a source is saved.
        '''
        initial_total = self.report.get_total_emissions()
        self.source.value = 2000
        self.source.save()
        self.assertNotEqual(initial_total, self.report.get_total_emissions())

    def test_update_report_emissions_on_source_delete(self):
        '''
        Test that report emissions are updated when a source is deleted.
        '''
        initial_total = self.report.get_total_emissions()
        self.source.delete()
        self.assertNotEqual(initial_total, self.report.get_total_emissions())
        self.assertEqual(self.report.get_total_emissions(), 0)

class ReductionStrategyTests(TestCase):
    '''
    Test cases for the ReductionStrategy model and related calculations.
    '''

    def setUp(self):
        '''
        Set up test data for the ReductionStrategy tests.
        '''
        self.report = Report.objects.create(name="Test Report", date=datetime.now().date())
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            description="Test source",
            method="DISTANCE",
            emission_factor=0.1,
            value=1000,
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2020,
            uncertainty=5
        )
        self.strategy = ReductionStrategy.objects.create(name="Test Strategy")
        self.report.reduction_strategies.add(self.strategy)

    def test_calculate_total_reduction(self):
        '''
        Test the calculation of total reduction for a non-progressive modification.
        '''
        # Non-progressive modification
        Modification.objects.create(
            reduction_strategy=self.strategy,
            source=self.source,
            modification_type="VALUE",
            value=0.9,  # 10% reduction
            order=1,
            start_year=2022,
            end_year=2024,
            is_progressive=False
        )

        reduction_2022 = calculate_total_reduction(self.strategy, 2022, 2022)
        annual_emission = self.source.calculate_emission_for_year(2022)
        expected_reduction_2022 = annual_emission * 0.1  # 10% of annual emission
        self.assertAlmostEqual(reduction_2022, expected_reduction_2022, places=2)

        reduction_2022_2024 = calculate_total_reduction(self.strategy, 2022, 2024)
        expected_reduction_2022_2024 = expected_reduction_2022 * 3  # 3 years of 10% reduction
        self.assertAlmostEqual(reduction_2022_2024, expected_reduction_2022_2024, places=2)

    def test_calculate_total_reduction_with_progressive_modification(self):
        '''
        Test the calculation of total reduction for a progressive modification.
        '''
        self.strategy.modifications.all().delete()
        Modification.objects.create(
            reduction_strategy=self.strategy,
            source=self.source,
            modification_type="VALUE",
            value=Decimal('1.0'),
            order=1,
            start_year=2022,
            end_year=2024,
            is_progressive=True,
            target_value=Decimal('2000')  # Double the original value
        )
        reduction_2022_2024 = calculate_total_reduction(self.strategy, 2022, 2024)
        annual_emission = Decimal('0.1') * Decimal('1000') * Decimal('1')  # Total emission without considering lifetime
        expected_increase = sum([
            annual_emission * (Decimal('1') / Decimal('3')),  # 2022
            annual_emission * (Decimal('2') / Decimal('3')),  # 2023
            annual_emission * Decimal('1')                    # 2024
        ])
        print(f"Calculated reduction: {reduction_2022_2024}")
        print(f"Expected increase: {expected_increase}")
        self.assertAlmostEqual(reduction_2022_2024, -expected_increase, places=2)

class ModificationModelTest(TestCase):
    '''
    Test cases for the Modification model.
    '''

    def setUp(self):
        '''
        Set up test data for the Modification model tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            emission_factor=Decimal('0.1'),
            value=Decimal('1000'),
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )
        self.strategy = ReductionStrategy.objects.create(name="Test Strategy")
        self.report.reduction_strategies.add(self.strategy)
        self.modification = Modification.objects.create(
            reduction_strategy=self.strategy,
            source=self.source,
            modification_type="VALUE",
            value=Decimal('0.9'),
            order=1,
            start_year=2024,
            end_year=2026,
            is_progressive=False,
            calculation_year=2025
        )

    def test_modification_creation(self):
        '''
        Test that a Modification object is created correctly.
        '''
        self.assertEqual(self.modification.reduction_strategy, self.strategy)
        self.assertEqual(self.modification.source, self.source)
        self.assertEqual(self.modification.modification_type, "VALUE")
        self.assertEqual(self.modification.value, Decimal('0.9'))

    def test_calculate_modified_emission(self):
        '''
        Test the calculation of modified emissions for a non-progressive modification.
        '''
        base_emission = Decimal('100')
        modified = self.modification.calculate_modified_emission(base_emission)
        self.assertEqual(modified, Decimal('90'))  # 90% of base emission

    def test_progressive_modification(self):
        '''
        Test the calculation of modified emissions for a progressive modification.
        '''
        prog_mod = Modification.objects.create(
            reduction_strategy=self.strategy,
            source=self.source,
            modification_type="VALUE",
            value=Decimal('1.0'),
            start_year=2024,
            end_year=2026,
            is_progressive=True,
            target_value=Decimal('2000'),
            calculation_year=2025
        )
        base_emission = Decimal('100')
        modified = prog_mod.calculate_modified_emission(base_emission)
        expected = base_emission * (Decimal('1000') + (Decimal('2000') - Decimal('1000')) * (Decimal('2') / Decimal('3'))) / Decimal('1000')
        self.assertAlmostEqual(modified, expected, places=2)

class EdgeCaseModelTests(TestCase):
    '''
    Test cases for edge cases in the emissions models.
    '''

    def test_future_acquisition_year(self):
        '''
        Test the behavior of a source with a future acquisition year.
        '''
        future_year = datetime.now().year + 5
        report = Report.objects.create(name="Future Report", date="2023-01-01")
        source = Source.objects.create(
            name="Future Source",
            report=report,
            category="TRANSPORT",
            emission_factor=0.1,
            value=1000,
            quantity=1,
            lifetime=5,
            acquisition_year=future_year,
            uncertainty=5
        )
        self.assertEqual(source.total_emission, 0)
        self.assertEqual(source.calculate_emission_for_year(datetime.now().year), 0)

    def test_modification_outside_source_lifetime(self):
        '''
        Test the behavior of a modification applied outside the source's lifetime.
        '''
        report = Report.objects.create(name="Test Report", date="2023-01-01")
        source = Source.objects.create(
            name="Test Source",
            report=report,
            category="TRANSPORT",
            emission_factor=Decimal('0.1'),
            value=1000,
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )
        strategy = ReductionStrategy.objects.create(name="Test Strategy")
        report.reduction_strategies.add(strategy)
        modification = Modification.objects.create(
            reduction_strategy=strategy,
            source=source,
            modification_type="VALUE",
            value=Decimal('0.9'),
            order=1,
            start_year=2029,  # Outside the source's lifetime
            calculation_year=2029
        )
        self.assertEqual(modification.calculate_modified_emission(), Decimal('0'))

# ——————————————————————————————— Integration tests ————————————————————————————————————

class EmissionIntegrationTests(TestCase):
    '''
    Integration tests for the emissions calculation system.
    '''

    def setUp(self):
        '''
        Set up test data for the integration tests.
        '''
        self.client = APIClient()
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            description="Test description",
            method="DISTANCE",
            emission_factor=Decimal('0.1'),
            value=Decimal('1000'),
            value_unit="km",
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=Decimal('5.0')
        )
        self.strategy = ReductionStrategy.objects.create(name="Test Strategy")
        self.report.reduction_strategies.add(self.strategy)

    def test_create_modification_and_calculate_reduction(self):
        '''
        Test creating a modification and calculating the resulting reduction.
        '''
        # Create a new modification
        modification_data = {
            "reduction_strategy": self.strategy.id,
            "source": self.source.id,
            "modification_type": "VALUE",
            "value": Decimal('0.9'),
            "order": 1,
            "start_year": 2024,
            "is_progressive": False
        }
        response = self.client.post(reverse('modification-list'), modification_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Calculate total reduction
        response = self.client.get(reverse('reductionstrategy-total-reduction', args=[self.strategy.id]), {'start_year': 2024, 'end_year': 2025})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the calculated reduction
        reduction_data = response.json()
        self.assertIn('total_reduction', reduction_data)
        self.assertGreater(Decimal(reduction_data['total_reduction']), Decimal('0'))

    def test_add_multiple_strategies_to_report(self):
        '''
        Test adding multiple reduction strategies to a report.
        '''
        strategy2 = ReductionStrategy.objects.create(name="Test Strategy 2")

        # Check initial state
        print(f"Initial strategies: {list(self.report.reduction_strategies.all())}")
        print(f"Strategy 1 ID: {self.strategy.id}, Strategy 2 ID: {strategy2.id}")

        response = self.client.post(reverse('report-add-strategy', args=[self.report.id]), {'strategy_id': strategy2.id})
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.report.refresh_from_db()
        print(f"Strategies after adding: {list(self.report.reduction_strategies.all())}")

        self.assertEqual(self.report.reduction_strategies.count(), 2)
        self.assertIn(self.strategy, self.report.reduction_strategies.all())
        self.assertIn(strategy2, self.report.reduction_strategies.all())

        if self.report.reduction_strategies.count() != 2:
            print(f"Strategy 1 (ID: {self.strategy.id}) in report: {self.strategy in self.report.reduction_strategies.all()}")
            print(f"Strategy 2 (ID: {strategy2.id}) in report: {strategy2 in self.report.reduction_strategies.all()}")
            print(f"All strategies in report: {self.report.reduction_strategies.all()}")

class APIEndpointTests(APITestCase):
    '''
    Test cases for API endpoints.
    '''

    def setUp(self):
        '''
        Set up test data for API endpoint tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")
        self.source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            emission_factor=0.1,
            value=1000,
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )

    def test_report_list(self):
        '''
        Test the report list endpoint.
        '''
        url = reverse('report-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_source_list(self):
        '''
        Test the source list endpoint.
        '''
        url = reverse('source-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_report_detail(self):
        '''
        Test the report detail endpoint.
        '''
        url = reverse('report-detail', args=[self.report.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Test Report")

class EdgeCaseAPITests(APITestCase):
    '''
    Test cases for edge cases in API interactions.
    '''

    def setUp(self):
        '''
        Set up test data for edge case API tests.
        '''
        self.report = Report.objects.create(name="Test Report", date="2023-01-01")

    def test_create_source_future_acquisition(self):
        '''
        Test creating a source with a future acquisition year.
        '''
        future_year = datetime.now().year + 5
        url = reverse('source-list')
        data = {
            "name": "Future Source",
            "report": self.report.id,
            "category": "TRANSPORT",
            "description": "Test description",
            "method": "DISTANCE",
            "emission_factor": 0.1,
            "value": 1000,
            "value_unit": "km",
            "quantity": 1,
            "lifetime": 5,
            "acquisition_year": future_year,
            "uncertainty": 5,
            "year": datetime.now().year
        }
        print(f"Sending data: {data}")
        response = self.client.post(url, data, format='json')
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")

        if response.status_code != status.HTTP_201_CREATED:
            print(f"Detailed response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        if response.status_code == status.HTTP_201_CREATED:
            created_source = Source.objects.get(id=response.data['id'])
            self.assertEqual(created_source.total_emission, 0)
            self.assertEqual(created_source.report_id, self.report.id)
        else:
            self.fail(f"Failed to create source. Errors: {response.content}")

    def test_calculate_emissions_before_acquisition(self):
        '''
        Test calculating emissions for years before the source's acquisition year.
        '''
        source = Source.objects.create(
            name="Test Source",
            report=self.report,
            category="TRANSPORT",
            emission_factor=0.1,
            value=1000,
            quantity=1,
            lifetime=5,
            acquisition_year=2023,
            uncertainty=5
        )
        url = reverse('source-emissions-by-year', args=[source.id])
        response = self.client.get(url, {'start_year': 2020, 'end_year': 2025})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Convert expected keys to int before comparison
        self.assertEqual(response.data[int('2020')], 0)
        self.assertEqual(response.data[int('2021')], 0)
        self.assertEqual(response.data[int('2022')], 0)
        self.assertGreater(response.data[int('2023')], 0)