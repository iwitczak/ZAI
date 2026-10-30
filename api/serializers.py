# series/serializers.py
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers


class SeriesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    minValue = serializers.FloatField(source="min_value")
    maxValue = serializers.FloatField(source="max_value")
    color = serializers.CharField()
    icon = serializers.CharField(allow_null=True)
    unit = serializers.CharField(allow_null=True)


class SensorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    seriesId = serializers.IntegerField(source="series_id")
    createdAt = serializers.DateTimeField(source="created_at")
    lastMeasurementAt = serializers.DateTimeField(
        source="last_measurement_at", default=None, allow_null=True
    )


class MeasurementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    value = serializers.FloatField()
    timestamp = serializers.DateTimeField()
    sensorId = serializers.IntegerField(source="sensor_id")
    seriesId = serializers.IntegerField(source="sensor.series_id")


class TimestampSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField() 

    def validate_timestamp(self, value):
        now = timezone.now()

        if value > now + timedelta(minutes=5):
            raise serializers.ValidationError("Timestamp must not be from the future.")

        return value


class DateRangeSerializer(serializers.Serializer):
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["date_to"] < attrs["date_from"]:
            raise serializers.ValidationError(
                {"to": "Date to cannot be earlier than date from."}
            )
        return attrs
