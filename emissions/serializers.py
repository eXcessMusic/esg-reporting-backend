from django.urls import reverse
from rest_framework import serializers
from .models import Report, Source, ReductionStrategy, Modification
import logging

logger = logging.getLogger(__name__)

class ReductionStrategySerializer(serializers.HyperlinkedModelSerializer):
    '''
    Serializer for the ReductionStrategy model.
    '''
    class Meta:
        model = ReductionStrategy
        fields = ['url', 'id', 'name', 'created_at']
        extra_kwargs = {
            'url': {'view_name': 'reductionstrategy-detail', 'lookup_field': 'pk'}
        }

class ReportSerializer(serializers.HyperlinkedModelSerializer):
    '''
    Serializer for the Report model.
    Includes nested ReductionStrategy serializers.
    '''
    reduction_strategies = ReductionStrategySerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ['url', 'id', 'name', 'date', 'reduction_strategies', 'total_emissions_cache']
        extra_kwargs = {
            'url': {'view_name': 'report-detail', 'lookup_field': 'pk'}
        }

class SourceSerializer(serializers.HyperlinkedModelSerializer):
    '''
    Serializer for the Source model.
    Includes calculated fields for total and annual emissions.
    '''
    total_emission = serializers.FloatField(read_only=True)
    annual_emission = serializers.FloatField(read_only=True)
    report = serializers.PrimaryKeyRelatedField(queryset=Report.objects.all(), required=True)

    class Meta:
        model = Source
        fields = ['url', 'id', 'name', 'report', 'category', 'description', 'method',
                    'emission_factor', 'value', 'value_unit', 'quantity',
                    'lifetime', 'acquisition_year', 'uncertainty', 'annual_emission', 'total_emission', 'year']
        extra_kwargs = {
            'url': {'view_name': 'source-detail', 'lookup_field': 'pk'}
        }

    def validate(self, attrs):
        '''
        Perform cross-field validation for the Source model.
        '''
        logger.debug(f"Validating data: {attrs}")
        # Add any cross-field validation here
        return attrs

    def to_internal_value(self, data):
        '''
        Convert the initial data into the format expected by the model.
        '''
        logger.debug(f"Converting to internal value: {data}")
        try:
            return super().to_internal_value(data)
        except Exception as e:
            logger.error(f"Error in to_internal_value: {str(e)}")
            raise

    def create(self, validated_data):
        '''
        Create and return a new Source instance, given the validated data.
        '''
        logger.debug(f"Creating source with data: {validated_data}")
        try:
            return super().create(validated_data)
        except Exception as e:
            logger.error(f"Error creating source: {str(e)}")
            raise

class ModificationSerializer(serializers.HyperlinkedModelSerializer):
    '''
    Serializer for the Modification model.
    Handles the relationships with ReductionStrategy and Source models.
    '''
    reduction_strategy = serializers.HyperlinkedRelatedField(
        view_name='reductionstrategy-detail',
        queryset=ReductionStrategy.objects.all(),
        lookup_field='pk'
    )
    source = serializers.HyperlinkedRelatedField(
        view_name='source-detail',
        queryset=Source.objects.all(),
        lookup_field='pk'
    )

    class Meta:
        model = Modification
        fields = [
            'url', 'id', 'reduction_strategy', 'source', 'modification_type',
            'value', 'order', 'start_year', 'end_year', 'is_progressive',
            'target_value', 'calculation_year'
        ]
        extra_kwargs = {
            'url': {'view_name': 'modification-detail', 'lookup_field': 'pk'},
        }

    def to_internal_value(self, data):
        '''
        Convert the initial data into the format expected by the model.
        Handles conversion of IDs to URLs for related fields.
        '''
        data = data.copy()  # Create a mutable copy of the data
        request = self.context.get('request')

        if request:
            for field in ['reduction_strategy', 'source']:
                if field in data:
                    value = data[field]
                    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                        # If it's an ID, convert it to a URL
                        url_name = 'reductionstrategy-detail' if field == 'reduction_strategy' else 'source-detail'
                        url = reverse(url_name, args=[value])
                        data[field] = request.build_absolute_uri(url)
                    elif isinstance(value, str) and not value.startswith('http'):
                        # If it's a string but not a URL, assume it's a relative URL and make it absolute
                        data[field] = request.build_absolute_uri(value)

        return super().to_internal_value(data)

    def create(self, validated_data):
        '''
        Create and return a new Modification instance, given the validated data.
        '''
        logger.debug(f"Creating modification with data: {validated_data}")
        return super().create(validated_data)