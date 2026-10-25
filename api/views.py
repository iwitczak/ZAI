from django.http import JsonResponse
from rest_framework.views import APIView, Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from api.models import Sensor, Series, Measurement
from api.serializers import MeasurementSerializer, SensorSerializer, SeriesSerializer
from utils.common_classes import ProblemJSONContent, ProblemJSONResponse
from utils.wrappers import auth_required

import logging
L = logging.getLogger(__name__)


class HealthView(APIView):
    def get(self, request):
        data = {'status': 'ok'}
        return JsonResponse(data)

# *** SERIES ***
class SeriesView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request):
        # Get all Series
        series_data = Series.get_all_series()
        response = SeriesSerializer(series_data, many=True).data
        return JsonResponse(response, status=200)

    @auth_required
    def post(self, request):
        # Create a new Series
        # Required params
        r_name = request.data.get('name')
        r_min_value = request.data.get('minValue')
        r_max_value = request.data.get('maxValue')
        r_color = request.data.get('color')

        L.debug(f'{r_name}, {r_min_value}, {r_max_value}, {r_color}')

        if not isinstance(r_name, str) or not isinstance(r_color, str) or not isinstance(r_min_value, int) or not isinstance(r_max_value, int):
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=400, 
                errors={'name': 'This field is required as string.', 'color': 'This field is required as string.', 'minValue': 'This field is required as integer.', 'maxValue': 'This field is required as integer.'}
                ).get_response()

        if r_min_value >= r_max_value:
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=422, 
                errors={'minValue': 'Value of this field must be smaller than maxValue.'}
                ).get_response()

        # Not required params
        r_icon = request.data.get('icon')
        r_unit = request.data.get('unit')

        # Create new Series element
        series = Series.create_series(name=r_name, min_value=r_min_value, max_value=r_max_value, color=r_color, icon=r_icon, unit=r_unit)
        series_json = SeriesSerializer(series).data
        return JsonResponse(series_json, status=201, safe=False, headers={"Location": f'api/series/{series.pk}/'})



class SeriesSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request, id):
        series = Series.get_series_by_id(id)
        if series is not None:
            L.debug(SeriesSerializer(series).data)
            return JsonResponse(SeriesSerializer(series).data, status=200)
        return Response(status=404)

    @auth_required
    def put(self, request, id):
        # Required params
        r_name = request.data.get('name')
        r_min_value = request.data.get('minValue')
        r_max_value = request.data.get('maxValue')
        r_color = request.data.get('color')

        L.debug(f'{r_name}, {r_min_value}, {r_max_value}, {r_color}')

        if not isinstance(r_name, str) or not isinstance(r_color, str) or not isinstance(r_min_value, int) or not isinstance(r_max_value, int):
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=400, 
                errors={'name': 'This field is required as string.', 'color': 'This field is required as string.', 'minValue': 'This field is required as integer.', 'maxValue': 'This field is required as integer.'}
                ).get_response()

        if r_min_value >= r_max_value:
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=422, 
                errors={'minValue': 'Value of this field must be smaller than maxValue.'}
                ).get_response()

        # Not required params
        r_icon = request.data.get('icon')
        r_unit = request.data.get('unit')

        series = Series.get_series_by_id(id)
        if series is None:
            return Response(status=404)

        # Check current min and max values
        current_values = Measurement.get_min_max_values_by_series(series_id=id)
        if isinstance(current_values, dict):
            curr_min = current_values.get('min_v')
            curr_max = current_values.get('max_v')
            if curr_min is not None and r_min_value > curr_min or curr_max is not None and r_max_value < curr_max:
                errors = {}
                if curr_min is not None and r_min_value > curr_min:
                    errors['minValue'] = "New minValue is larger than min value currently in Series."
                if curr_max is not None and r_max_value < curr_max:
                    errors['maxValue'] = "New maxValue is smaller than max value currently in Series."

                return ProblemJSONResponse(
                    content=ProblemJSONContent.CONFLICT,
                    status=409,
                    errors=errors
                )

        _ = Series.update_series(series_id=id, name=r_name, min_value=r_min_value, max_value=r_max_value, color=r_color, icon=r_icon, unit=r_unit)

        new_series = Series.get_series_by_id(id)
        if new_series is None:
            return Response(status=404)
        return JsonResponse(data=SeriesSerializer(new_series).data, status=200) 

    @auth_required
    def delete(self, request, id):
        series = Series.get_series_by_id(id)
        if series is None:
            return Response(status=404)

        _ = Series.delete_series(id)
        return Response(status=204)


# *** SENSORS ***
class SensorView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    @auth_required
    def get(self, request):
        sensors = Sensor.get_all_sensors()

        response = SensorSerializer(sensors, many=True).data

        return Response(response, status=200)

    @auth_required
    def post(self, request):
        # Required params
        r_name = request.data.get('name')
        r_series_id = request.data.get('seriesId')

        if not isinstance(r_name, str) or not isinstance(r_series_id, int):
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=400, 
                errors={'name': 'This field is required as string.', 'seriesId': 'This field is required as integer.'}
            ).get_response()

        series = Series.get_series_by_id(r_series_id)
        if series is None:
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=422, 
                errors={'seriesId': 'Series with this id does not exist.'}
            ).get_response()

        sensor, raw_key = Sensor.create_sensor(name=r_name, series_id=r_series_id)
        response = {
            'id': sensor.pk,
            'name': sensor.name,
            'seriesId': sensor.series.pk,
            'createdAt': sensor.created_at,
            'lastMeasurementAt': None,
            'apiKey': raw_key
        }
        return Response(response, status=201)


class SensorSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    @auth_required
    def get(self, request, id):
        sensor = Sensor.get_sensor_by_id(id)
        if sensor is None:
            return Response(status=404)
        response = SensorSerializer(sensor).data
        return JsonResponse(response, status=201)


    @auth_required
    def delete(self, request, id):
        pass


# *** MEASUREMENTS ***
class MeasurementView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request):
        pass

    def post(self, request):
        pass


class MeasurementSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request, id):
        measurement = Measurement.get_measurement_by_id(id)
        if measurement is None:
            Response(status=404)
        response = MeasurementSerializer(measurement).data
        return JsonResponse(data=response, status=201)
