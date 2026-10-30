from django.urls import path
import api.views as v

urlpatterns = [
    path('health', v.HealthView.as_view(), name='api_health'),

    # SERIES
    path('series', v.SeriesView.as_view(), name='api_series'),
    path('series/<int:id>', v.SeriesSingleView.as_view(), name='api_series_single'),

    # MEASUREMENT
    path('measurements', v.MeasurementView.as_view(), name='api_measurement'),
    path('measurements/<int:id>', v.MeasurementSingleView.as_view(), name='api_measurement_single'),

    # SENSOR
    path('sensors', v.SensorView.as_view(), name='api_sensor'),
    path('sensors/<int:id>', v.SensorSingleView.as_view(), name='api_sensor_single'),
]