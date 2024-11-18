from decimal import Decimal
from django.forms import ValidationError
import numpy as np
from rest_framework import generics, viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.reverse import reverse
from django_filters import rest_framework as filters
from .models import Report, Source, ReductionStrategy, Modification
from .serializers import ReportSerializer, SourceSerializer, ReductionStrategySerializer, ModificationSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from datetime import datetime
import logging
from django.views.generic import TemplateView
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from .utils import NumpyEncoder
from django.http import JsonResponse


logger = logging.getLogger(__name__)

'''
TODO :
- Add authentication and authorization : permission_classes = [IsAuthenticated]
'''

class APIRoot(APIView):
    '''
    Root view for the API, providing links to main endpoints.
    '''
    def get(self, request, format=None):
        return Response({
            'reports': reverse('report-list', request=request, format=format),
            'sources': reverse('source-list', request=request, format=format),
            'reduction-strategies': reverse('reductionstrategy-list', request=request, format=format),
            'modifications': reverse('modification-list', request=request, format=format),
        })

class ContextMixin:
    '''
    Mixin to provide request context to serializers.
    '''
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

# And then use it like this:
# class ReportList(ContextMixin, generics.ListCreateAPIView):
#     ...


class ReportList(ContextMixin, generics.ListCreateAPIView):
    '''
    View for listing all reports or creating a new report.
    '''
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing reports: {str(e)}")
            return Response({"error": "An error occurred while retrieving reports"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating report: {str(e)}")
            return Response({"error": "An error occurred while creating the report"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportDetail(ContextMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    View for retrieving, updating or deleting a specific report.
    '''
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving report: {str(e)}")
            return Response({"error": "An error occurred while retrieving the report"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def sources(self, request, pk=None):
        '''
        Retrieve sources for a specific report.
        '''
        try:
            report = self.get_object()
            sources = Source.objects.filter(report=report)
            serializer = SourceSerializer(sources, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving sources for report {pk}: {str(e)}")
            return Response({"error": "An error occurred while retrieving sources"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def projected_emissions(self, request, pk=None):
        '''
        Calculate projected emissions for a report.
        '''
        try:
            report = self.get_object()
            year = int(request.query_params.get('year', datetime.now().year))
            strategy_ids = request.query_params.getlist('strategies')
            strategies = ReductionStrategy.objects.filter(id__in=strategy_ids) if strategy_ids else None

            projected = report.projected_total_emissions(year, strategies)
            return Response({'year': year, 'projected_emissions': projected})
        except ValueError:
            return Response({"error": "Invalid year parameter"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error calculating projected emissions for report {pk}: {str(e)}")
            return Response({"error": "An error occurred while calculating projected emissions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def add_strategy(self, request, pk=None):
        '''
        Add a reduction strategy to a report.
        '''
        try:
            report = self.get_object()
            strategy_id = request.data.get('strategy_id')
            if not strategy_id:
                return Response({"error": "Strategy ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            strategy = ReductionStrategy.objects.get(id=strategy_id)
            report.reduction_strategies.add(strategy)
            report.save()
            
            return Response({"status": "strategy added", "strategy_id": strategy.id}, status=status.HTTP_200_OK)
        except ReductionStrategy.DoesNotExist:
            return Response({"error": "Strategy not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error adding strategy to report {pk}: {str(e)}")
            return Response({"error": "An error occurred while adding the strategy"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def remove_strategy(self, request, pk=None):
        '''
        Remove a reduction strategy from a report.
        '''
        try:
            report = self.get_object()
            strategy_id = request.data.get('strategy_id')
            if not strategy_id:
                return Response({"error": "Strategy ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            strategy = ReductionStrategy.objects.get(id=strategy_id)
            report.reduction_strategies.remove(strategy)
            return Response({"status": "strategy removed"})
        except ReductionStrategy.DoesNotExist:
            return Response({"error": "Strategy not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error removing strategy from report {pk}: {str(e)}")
            return Response({"error": "An error occurred while removing the strategy"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ReportSourcesView(APIView):
    '''
    View to retrieve sources for a specific report.
    '''
    def get(self, request, pk):
        try:
            report = get_object_or_404(Report, pk=pk)
            sources = Source.objects.filter(report=report)
            serializer = SourceSerializer(sources, many=True, context={'request': request})
            return Response(serializer.data)
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving sources for report {pk}: {str(e)}")
            return Response({"error": "An error occurred while retrieving sources"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportProjectedEmissionsView(APIView):
    '''
    View to calculate projected emissions for a report.
    '''
    def get(self, request, pk):
        try:
            report = get_object_or_404(Report, pk=pk)
            
            # Validate year parameter
            current_year = datetime.now().year
            year = request.query_params.get('year')
            if year:
                try:
                    year = int(year)
                    if year < 1900 or year > current_year + 100:
                        raise ValidationError(f"Year must be between 1900 and {current_year + 100}")
                except ValueError:
                    raise ValidationError("Invalid year format. Please provide a valid integer.")
            else:
                year = current_year

            # Validate strategy IDs
            strategy_ids = request.query_params.getlist('strategies')
            if strategy_ids:
                try:
                    strategy_ids = [int(sid) for sid in strategy_ids]
                except ValueError:
                    raise ValidationError("Invalid strategy ID format. Please provide valid integers.")
                
                strategies = ReductionStrategy.objects.filter(id__in=strategy_ids)
                if len(strategies) != len(strategy_ids):
                    raise ValidationError("One or more strategy IDs are invalid.")
            else:
                strategies = None

            projected = report.projected_total_emissions(year, strategies)
            return Response({'year': year, 'projected_emissions': projected})

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error calculating projected emissions for report {pk}: {str(e)}")
            return Response({"error": "An error occurred while calculating projected emissions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportAddStrategyView(APIView):
    '''
    View to add a reduction strategy to a report.
    '''
    def post(self, request, pk):
        try:
            report = get_object_or_404(Report, pk=pk)
            strategy_id = request.data.get('strategy_id')
            if not strategy_id:
                return Response({"error": "Strategy ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            strategy = get_object_or_404(ReductionStrategy, id=strategy_id)
            report.reduction_strategies.add(strategy)
            report.save()
            
            return Response({"status": "strategy added", "strategy_id": strategy.id}, status=status.HTTP_200_OK)
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except ReductionStrategy.DoesNotExist:
            return Response({"error": "Strategy not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error adding strategy to report {pk}: {str(e)}")
            return Response({"error": "An error occurred while adding the strategy"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReportRemoveStrategyView(APIView):
    '''
    View to remove a reduction strategy from a report.
    '''
    def post(self, request, pk):
        try:
            report = get_object_or_404(Report, pk=pk)
            strategy_id = request.data.get('strategy_id')
            if not strategy_id:
                return Response({"error": "Strategy ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            strategy = get_object_or_404(ReductionStrategy, id=strategy_id)
            report.reduction_strategies.remove(strategy)
            return Response({"status": "strategy removed"})
        except Report.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except ReductionStrategy.DoesNotExist:
            return Response({"error": "Strategy not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error removing strategy from report {pk}: {str(e)}")
            return Response({"error": "An error occurred while removing the strategy"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SourceList(ContextMixin, generics.ListCreateAPIView):
    '''
    View for listing all sources or creating a new source.
    '''
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    filterset_fields = ['name', 'report', 'category', 'acquisition_year', 'year']

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating source: {str(e)}")
            return Response({"error": "An error occurred while creating the source"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SourceDetail(ContextMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    View for retrieving, updating or deleting a specific source.
    '''
    queryset = Source.objects.all()
    serializer_class = SourceSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Source.DoesNotExist:
            return Response({"error": "Source not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving source: {str(e)}")
            return Response({"error": "An error occurred while retrieving the source"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReductionStrategyList(ContextMixin, generics.ListCreateAPIView):
    '''
    View for listing all reduction strategies or creating a new one.
    '''
    queryset = ReductionStrategy.objects.all()
    serializer_class = ReductionStrategySerializer
    filterset_fields = ['report']

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating reduction strategy: {str(e)}")
            return Response({"error": "An error occurred while creating the reduction strategy"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReductionStrategyDetail(ContextMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    View for retrieving, updating or deleting a specific reduction strategy.
    '''
    queryset = ReductionStrategy.objects.all()
    serializer_class = ReductionStrategySerializer

    @action(detail=True, methods=['get'])
    def total_reduction(self, request, pk=None):
        '''
        Calculate total reduction for a strategy.
        '''
        try:
            strategy = self.get_object()
            start_year = request.query_params.get('start_year')
            end_year = request.query_params.get('end_year')

            if start_year:
                start_year = int(start_year)
            if end_year:
                end_year = int(end_year)

            total_reduction = calculate_total_reduction(strategy, start_year, end_year)

            original_emissions = strategy.reports.aggregate(
                total=Sum('sources__emission_factor') * Sum('sources__value') * Sum('sources__quantity')
            )['total'] or 0
            new_total_emissions = original_emissions - total_reduction

            reduction_percentage = (total_reduction / original_emissions) * 100 if original_emissions else 0

            return Response({
                'start_year': start_year,
                'end_year': end_year,
                'reference_emissions': original_emissions,
                'strategy_emissions': new_total_emissions,
                'total_reduction': total_reduction,
                'reduction_percentage': reduction_percentage
            })
        except ValueError:
            return Response({"error": "Invalid year parameter"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error calculating total reduction for strategy {pk}: {str(e)}")
            return Response({"error": "An error occurred while calculating total reduction"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def modifications(self, request, pk=None):
        '''
        Get modifications for a strategy.
        '''
        try:
            strategy = self.get_object()
            modifications = strategy.modifications.all()
            serializer = ModificationSerializer(modifications, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error retrieving modifications for strategy {pk}: {str(e)}")
            return Response({"error": "An error occurred while retrieving modifications"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ReductionStrategyTotalReductionView(APIView):
    def get(self, request, pk):
        strategy = get_object_or_404(ReductionStrategy, pk=pk)
        start_year = request.query_params.get('start_year')
        end_year = request.query_params.get('end_year')

        if start_year:
            start_year = int(start_year)
        if end_year:
            end_year = int(end_year)

        total_reduction = calculate_total_reduction(strategy, start_year, end_year)
        
        # Calculate original emissions
        original_emissions = sum(report.total_emissions(start_year) if start_year else report.total_emissions() 
                                for report in strategy.reports.all())

        new_total_emissions = Decimal(original_emissions) - total_reduction
        reduction_percentage = (total_reduction / Decimal(original_emissions)) * 100 if original_emissions else 0

        return Response({
            'start_year': start_year,
            'end_year': end_year,
            'reference_emissions': original_emissions,
            'strategy_emissions': new_total_emissions,
            'total_reduction': total_reduction,
            'reduction_percentage': reduction_percentage
        })

class ReductionStrategyModificationsView(APIView):
    def get(self, request, pk):
        strategy = get_object_or_404(ReductionStrategy, pk=pk)
        modifications = strategy.modifications.all()
        serializer = ModificationSerializer(modifications, many=True)
        return Response(serializer.data)

class ProjectionViewSet(ContextMixin, viewsets.ViewSet):
    '''
    ViewSet for handling emission projections.
    '''
    @action(detail=False, methods=['post'])
    def project_modifications(self, request):
        '''
        Project modifications for a source.
        '''
        try:
                # 1. Extract and validate input parameters
                source_id = request.data.get('source_id')
                modification_ids = request.data.get('modification_ids', [])
                start_year = int(request.data.get('start_year', datetime.now().year))
                requested_end_year = request.data.get('end_year')

                if not source_id:
                    return Response({"error": "Source ID is required"}, status=status.HTTP_400_BAD_REQUEST)

                # 2. Calculate max end year (50 years into the future)
                max_end_year = start_year + 50  # Time machines sold separately.

                # 3. Determine actual end year
                end_year = min(int(requested_end_year) if requested_end_year else max_end_year, max_end_year)

                # 4. Fetch source and modifications
                try:
                    source = Source.objects.get(id=source_id)
                    modifications = Modification.objects.filter(id__in=modification_ids).order_by('start_year', 'order')
                except Source.DoesNotExist:
                    return Response({"error": "Source not found"}, status=status.HTTP_404_NOT_FOUND)

                # 5. Calculate projections
                projected_emissions = project_emissions(source, modifications, start_year, end_year)

                # 6. Return results
                return Response({
                    "projections": {year: str(emission) for year, emission in projected_emissions.items()},
                    "start_year": start_year,
                    "end_year": end_year,
                    "max_allowed_end_year": max_end_year
                })

        except ValueError as e:
            logger.error(f"ValueError in project_modifications: {str(e)}")
            return Response({"error": f"Invalid input: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in project_modifications: {str(e)}")
            return Response({"error": "An unexpected error occurred", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModificationList(generics.ListCreateAPIView):
    '''
    View for listing all modifications or creating a new one.
    '''
    queryset = Modification.objects.all()
    serializer_class = ModificationSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating modification: {str(e)}")
            return Response({"error": "An error occurred while creating the modification"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModificationDetail(ContextMixin, generics.RetrieveUpdateDestroyAPIView):
    '''
    View for retrieving, updating or deleting a specific modification.
    '''
    queryset = Modification.objects.all()
    serializer_class = ModificationSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Modification.DoesNotExist:
            return Response({"error": "Modification not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving modification: {str(e)}")
            return Response({"error": "An error occurred while retrieving the modification"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardView(TemplateView):
    '''
    View for rendering the dashboard template.
    '''
    template_name = "emissions/dashboard.html"

@api_view(['GET'])
def source_emissions_by_year(request, pk):
    source = Source.objects.get(pk=pk)
    start_year = request.query_params.get('start_year')
    end_year = request.query_params.get('end_year')
    emissions_data = calculate_emissions_for_years(source, start_year, end_year)
    return Response(emissions_data)

@api_view(['GET'])
def source_total_emission(request, pk):
    source = Source.objects.get(pk=pk)
    total = source.total_emission
    return Response({"total_emission": total})

@api_view(['GET'])
def source_modifications(request, pk):
    source = Source.objects.get(pk=pk)
    modifications = source.modifications.all()
    serializer = ModificationSerializer(modifications, many=True, context={'request': request})
    return Response(serializer.data)

# —————————————— Helper functions —————————————————
def apply_modifications(emissions, source, modifications, years):
    '''
    Apply modifications to emissions.
    '''
    try:
        for mod in modifications:
            mod_mask = years >= mod.start_year
            if mod.end_year:
                mod_mask &= years <= mod.end_year

            if mod.is_progressive:
                total_years = mod.end_year - mod.start_year + 1
                years_passed = np.minimum(years[mod_mask] - mod.start_year + 1, total_years)
                progress = years_passed / total_years
                current_value = source.value + (mod.target_value - source.value) * progress
                emissions[mod_mask] *= (current_value / source.value).astype(float)
            elif mod.modification_type == 'VALUE':
                emissions[mod_mask] *= float(mod.value)
            else:  # 'EF'
                emissions[mod_mask] *= (float(mod.value) / float(source.emission_factor))
        return emissions
    except Exception as e:
        logger.error(f"Error applying modifications: {str(e)}")
        raise

def calculate_base_emissions(source, years):
    '''
    Calculate base emissions for a source.
    '''
    try:
        return np.array([float(source.calculate_emission_for_year(year)) for year in years])
    except Exception as e:
        logger.error(f"Error calculating base emissions: {str(e)}")
        raise

# Might need to slightly refactor this one too <-------------------------------------------
def project_emissions(source, modifications, start_year, end_year):
    '''
    Project emissions for a source with modifications.

    :param source: Source object
    :param modifications: QuerySet of Modification objects
    :param start_year: Start year for projection
    :param end_year: End year for projection
    :return: Dictionary of projected emissions by year
    '''
    try:
        years = range(start_year, end_year + 1)
        emissions = {}
        modified_value = Decimal(str(source.value))  # Ensure we start with a Decimal

        for year in years:
            # Check if the year is within the source's lifetime
            if year < source.acquisition_year or year >= source.acquisition_year + source.lifetime:
                emissions[str(year)] = Decimal('0')
                continue

            for modification in modifications:
                if modification.start_year <= year and (modification.end_year is None or year <= modification.end_year):
                    if modification.is_progressive:
                        total_years = Decimal(str(modification.end_year - modification.start_year + 1))
                        years_passed = Decimal(str(min(year - modification.start_year + 1, total_years)))
                        progress = years_passed / total_years
                        modified_value = Decimal(str(source.value)) + (Decimal(str(modification.target_value)) - Decimal(str(source.value))) * progress
                    else:
                        # For non-progressive modifications, apply the modification once
                        if year == modification.start_year:
                            modified_value *= Decimal(str(modification.value))

            modified_emission = (Decimal(str(source.emission_factor)) * modified_value * Decimal(str(source.quantity))) / Decimal(str(source.lifetime))
            emissions[str(year)] = modified_emission

        return emissions
    except Exception as e:
        logger.error(f"Error in project_emissions: {str(e)}")
        raise

def projected_total_emissions(self, year):
    '''
    Calculate projected total emissions for a report in a specific year.

    :param year: Year for which to calculate projected emissions
    :return: Total projected emissions for the year
    '''
    try:
        total_emissions = Decimal('0')
        for source in self.sources.all():
            emission = source.calculate_emission_for_year(year)
            for strategy in self.reduction_strategies.all():
                modifications = strategy.modifications.filter(source=source, start_year__lte=year)
                for modification in modifications:
                    emission = modification.calculate_modified_emission(emission)
            total_emissions += emission
        return total_emissions
    except Exception as e:
        logger.error(f"Error in projected_total_emissions for year {year}: {str(e)}")
        raise

def calculate_emissions_for_years(source, start_year, end_year):
    '''
    Calculate emissions for a source over a range of years.
    '''
    try:
        current_year = datetime.now().year
        start_year = int(start_year) if start_year else source.acquisition_year
        end_year = int(end_year) if end_year else current_year

        # Generate years as a numpy array
        years = np.arange(start_year, end_year + 1)
        
        # Calculate emissions for each year
        emissions = [source.calculate_emission_for_year(year) for year in years]

        # Convert numpy.int64 years to Python int and create the dictionary
        return {int(year): emission for year, emission in zip(years, emissions)}
    except Exception as e:
        logger.error(f"Error calculating emissions for years: {str(e)}")
        raise

def calculate_total_reduction(strategy, start_year=None, end_year=None, report=None):
    if start_year is None:
        start_year = datetime.now().year
    if end_year is None:
        end_year = start_year

    reports = [report] if report else strategy.reports.all()
    years = np.arange(start_year, end_year + 1)
    total_reduction = Decimal('0')

    for report in reports:
        sources = report.sources.all().prefetch_related('modifications')
        
        emission_factors = np.array([float(source.emission_factor) for source in sources])
        values = np.array([float(source.value) for source in sources])
        quantities = np.array([float(source.quantity) for source in sources])
        acquisition_years = np.array([source.acquisition_year for source in sources])
        lifetimes = np.array([source.lifetime for source in sources])

        for year in years:
            active_mask = (acquisition_years <= year) & (year < acquisition_years + lifetimes)
            original_emissions = np.where(active_mask, emission_factors * values * quantities, 0)
            modified_emissions = original_emissions.copy()

            modifications = strategy.modifications.filter(start_year__lte=year, source__in=sources)
            for mod in modifications:
                mod_mask = active_mask & (mod.source.id == np.array([s.id for s in sources]))
                if mod.is_progressive:
                    progress = Decimal(min((year - mod.start_year + 1) / (mod.end_year - mod.start_year + 1), 1))
                    current_value = Decimal(values[mod_mask][0]) + (Decimal(mod.target_value) - Decimal(values[mod_mask][0])) * progress
                    modified_emissions[mod_mask] = float(Decimal(emission_factors[mod_mask][0]) * current_value * Decimal(quantities[mod_mask][0]))
                elif mod.modification_type == 'VALUE':
                    modified_emissions[mod_mask] *= float(mod.value)
                elif mod.modification_type == 'EF':
                    modified_emissions[mod_mask] *= (float(mod.value) / emission_factors[mod_mask])

            total_reduction += Decimal(str(np.sum(original_emissions - modified_emissions)))

    return total_reduction

def calculate_source_emissions(source, year):
    if year < source.acquisition_year or year >= source.acquisition_year + source.lifetime:
        return 0
    annual_emission = source.total_emission / source.lifetime
    return annual_emission