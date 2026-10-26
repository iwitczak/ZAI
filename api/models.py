import hashlib
import secrets

from django.db import models
from django.core.validators import MinLengthValidator
from django.db.models.aggregates import Max, Min
from django.utils.timezone import now, timedelta

# 1. Series
class Series(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    min_value = models.FloatField()
    max_value = models.FloatField()
    color = models.CharField(max_length=7)  # Hex color code
    icon = models.CharField(max_length=255, null=True, blank=True)
    unit = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(min_value__lt=models.F('max_value')), name='min_value_lt_max_value', violation_error_message="Min value must be smaller than max value."),
            models.CheckConstraint(condition=models.Q(color__regex=r'^#[0-9A-Fa-f]{6}$'), name='valid_hex_color', violation_error_message="Invalid hex color format."),
        ]

    # Return all series
    @classmethod
    def get_all_series(cls):
        return cls.objects.all()


    @classmethod
    def create_series(cls, name, min_value, max_value, color, icon=None, unit=None):
        series = Series(name=name, min_value=min_value, max_value=max_value, color=color, icon=icon, unit=unit)
        series.full_clean()
        series.save()
        return series

    @classmethod
    def get_series_by_id(cls, series_id):
        """Returns Series object or None"""
        return cls.objects.filter(id=series_id).first()

    @classmethod
    def update_series(cls, series_id, name, min_value, max_value, color, icon=None, unit=None):
        return cls.objects.filter(id=series_id).update(name=name, min_value=min_value, max_value=max_value, color=color, icon=icon, unit=unit)
        
    @classmethod
    def delete_series(cls, series_id):
        return cls.objects.filter(id=series_id).delete()


# 2. Sensor
class Sensor(models.Model):
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    api_key_hash = models.CharField(max_length=64, unique=True, editable=False)  # SHA-256 hash of the API key
    created_at = models.DateTimeField(default=now())
    is_active = models.BooleanField(default=True) # When False, api key is invalidated and sensor cannot send measurements anymore

    series = models.ForeignKey(Series, on_delete=models.CASCADE)

    @classmethod
    def _generate_api_key(cls):
        return secrets.token_urlsafe(32)

    @classmethod
    def _get_api_key_hash(cls, raw_api_key):
        return hashlib.sha256(raw_api_key.encode()).hexdigest()

    @classmethod
    def _get_query_with_last_measurement(cls):
        return cls.objects.annotate(last_measurement_at=Max("measurement__timestamp"))

    @classmethod
    def get_sensor_by_api_key(cls, api_key):
        """Returns Sensor object or None"""
        return cls.objects.filter(api_key_hash=cls._get_api_key_hash(api_key), is_active=True).first()

    @classmethod
    def get_all_sensors(cls):
        return cls._get_query_with_last_measurement().all()

    @classmethod
    def create_sensor(cls, name, series_id):
        raw_key = cls._generate_api_key()
        key_hash = cls._get_api_key_hash(raw_key)
        sensor = Sensor(name=name, api_key_hash=key_hash, series_id=series_id)
        sensor.full_clean()
        sensor.save()
        sensor.api_key_hash = None  # Hide the hash when returning the object
        return sensor, raw_key

    @classmethod
    def get_sensor_by_id(cls, sensor_id):
        return cls._get_query_with_last_measurement().filter(id=sensor_id).first() # .values('id', 'name', 'series', 'created_at', 'last_measurement_at')

    @classmethod
    def unregister_sensor(cls, sensor_id):
        return cls.objects.filter(id=sensor_id).update(is_active=False)
    

# 3. Measurement
class Measurement(models.Model):
    value = models.FloatField()
    timestamp = models.DateTimeField(default=now())

    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)  # When Sensor is deleted, delete all associated measurements


    @classmethod
    def get_measurements(cls, from_timestamp=None, to_timestamp=None, series=None, order_by='timestamp', limit=1000):
        # If series is empty, return all
        if series:
            queryset = cls.objects.filter(sensor__series__id__in=series)
        else:
            queryset = cls.objects.all()

        from_timestamp = from_timestamp or now() - timedelta(days=1)
        to_timestamp = to_timestamp or now()

        return queryset.filter(timestamp__gte=from_timestamp, timestamp__lte=to_timestamp).order_by(order_by)[:limit]

    @classmethod
    def create_measurement(cls, value, timestamp, sensor_id):
        # sensor_id = Sensor.get_sensor_by_api_key(api_key)
        # if not sensor_id:
        #     return None
        measurement = cls.objects.create(value=value, timestamp=timestamp, sensor=sensor_id)
        return measurement

    @classmethod
    def get_measurement_by_id(cls, measurement_id):
        return cls.objects.filter(id=measurement_id).first() # .values('id', 'value', 'timestamp', 'sensor', 'sensor__series')

    @classmethod
    def get_min_max_values_by_series(cls, series_id) -> dict | None:
        return cls.objects.filter(sensor__series__id=series_id).aggregate(min_v = Min('value'), max_v = Max('value'))
