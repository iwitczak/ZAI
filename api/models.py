from django.db import models

# 1. Series
class Series(models.Model):
    name = models.CharField(max_length=255)
    min_value = models.FloatField()
    max_value = models.FloatField()
    color = models.CharField(max_length=7)  # Hex color code
    icon = models.CharField(max_length=255)
    unit = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(min_value__lte=models.F('max_value')), name='min_value_lt_max_value'),
            models.CheckConstraint(condition=models.Q(color__regex=r'^#[0-9A-Fa-f]{6}$'), name='valid_hex_color'),
        ]

    # Return all series
    @classmethod
    def get_all_series(cls):
        pass


    # Create series
    @classmethod
    def create_series(cls, name, min_value, max_value, color, icon, unit):
        series = cls(name=name, min_value=min_value, max_value=max_value, color=color, icon=icon, unit=unit)
        series.save()
        return series

    @classmethod
    def get_series_by_id(cls, series_id):
        pass

    @classmethod
    def update_series(cls, series_id, **kwargs):
        pass

    @classmethod
    def delete_series(cls, series_id):
        pass
    


# 2. Sensor
class Sensor(models.Model):
    name = models.CharField(max_length=255) # ??? Should be unique?
    api_key_hash = models.CharField(max_length=64, unique=True, editable=False)  # SHA-256 hash of the API key
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) # When False, api key is invalidated and sensor cannot send measurements anymore

    series_id = models.ForeignKey(Series, related_name='sensors', on_delete=models.CASCADE) # When Series is deleted, delete all associated sensors

    @classmethod
    def _generate_api_key(cls):
        pass

    @classmethod
    def _get_api_key_hash(cls, api_key):
        pass

    @classmethod
    def get_all_sensors(cls):
        pass

    @classmethod
    def create_sensor(cls, name, series_id):
        pass

    @classmethod
    def get_sensor_by_id(cls, sensor_id):
        pass

    @classmethod
    def unregister_sensor(cls, sensor_id):
        pass

# 3. Measurement
class Measurement(models.Model):
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    sensor_id = models.ForeignKey(Sensor, related_name='measurements', on_delete=models.CASCADE)  # When Sensor is deleted, delete all associated measurements


    @classmethod
    def get_measurements(cls, from_timestamp=None, to_timestamp=None, series=[], sort_order='asc', limit=1000):
        # If series is empty, return all
        pass

    @classmethod
    def create_measurement(cls, api_key, value, timestamp):
        pass

    @classmethod
    def get_measurement_by_id(cls, measurement_id):
        pass
