from datetime import timedelta
import re

from django.http import JsonResponse
from django.utils.timezone import now
from rest_framework.views import APIView, Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from api.models import Sensor, Series, Measurement
from api.serializers import DateRangeSerializer, MeasurementSerializer, SensorSerializer, SeriesSerializer, TimestampSerializer
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
        return JsonResponse(response, status=200, safe=False)

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
        return JsonResponse(series_json, status=201, safe=False, headers={"Location": f'/api/series/{series.pk}'})



class SeriesSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request, id):
        series = Series.get_series_by_id(id)
        if series is not None:
            L.debug(SeriesSerializer(series).data)
            return JsonResponse(SeriesSerializer(series).data, status=200)
        return ProblemJSONResponse(ProblemJSONContent.NOT_FOUND, errors={'id': 'Series with provided id was not found.'}, status=404).get_response()

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
                ).get_response()

        _ = Series.update_series(series_id=id, name=r_name, min_value=r_min_value, max_value=r_max_value, color=r_color, icon=r_icon, unit=r_unit)

        new_series = Series.get_series_by_id(id)
        if new_series is None:
            return ProblemJSONResponse(ProblemJSONContent.NOT_FOUND, errors={'id': 'Series with provided id was not found.'}, status=404).get_response()
        return JsonResponse(data=SeriesSerializer(new_series).data, status=200) 

    @auth_required
    def delete(self, request, id):
        series = Series.get_series_by_id(id)
        if series is None:
            return ProblemJSONResponse(ProblemJSONContent.NOT_FOUND, errors={'id': 'Series with provided id was not found.'}, status=404).get_response()

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
        return Response(response, status=201, headers={"Location": f'/api/measurements/{sensor.pk}'})


class SensorSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    @auth_required
    def get(self, request, id):
        sensor = Sensor.get_sensor_by_id(id)
        if sensor is None:
            return Response(status=404)
        response = SensorSerializer(sensor).data
        return JsonResponse(response, status=200)


    @auth_required
    def delete(self, request, id):
        sensor = Sensor.get_sensor_by_id(id)
        if sensor is None:
            return Response(status=404)

        if not sensor.is_active:
            return ProblemJSONResponse(
                    content=ProblemJSONContent.CONFLICT,
                    status=409,
                    errors={'id': 'Sensor with this id is not active'}
                ).get_response()

        _ = Sensor.unregister_sensor(id)

        return Response(status=204)


# *** MEASUREMENTS ***
class MeasurementView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request):
        # Get params
        r_series = request.query_params.get('series')
        r_sort = request.query_params.get('sort', 'timestamp')
        r_limit = request.query_params.get('limit', 1000)
        r_time_from = request.query_params.get('from')
        r_time_to = request.query_params.get('to')
        L.debug(f'{r_series}, {r_sort} {r_limit} {r_time_from} {r_time_to}')

        # Parse series array
        series_regex = re.compile(r"^\s*\d+(\s*,\s*\d+)*\s*$")
        if isinstance(r_series, str) and r_series != '' and series_regex.fullmatch(r_series):
            series = r_series.strip().split(',')
        elif r_series == None:
            series = None
        else:
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=400, 
                errors={'series': 'This parameter must be comma separated string or empty'}
            ).get_response()

        # Parse sort
        if r_sort == '-timestamp':
            sort = '-timestamp'
        else:
            sort = 'timestamp'

        # Parse limit
        if isinstance(r_limit, int):
            limit = r_limit 
        else:
            return ProblemJSONResponse(
                ProblemJSONContent.INVALID_REQUEST, 
                status=400, 
                errors={'limit': 'This parameter must be int or empty'}
            ).get_response()

        # Parse time
        time_to = None
        time_from = None
        if r_time_from is not None and r_time_to is not None:
            time_serializer = DateRangeSerializer(data = {'date_from': r_time_from, 'date_to': r_time_to})
            if not time_serializer.is_valid():
                return ProblemJSONResponse(
                    ProblemJSONContent.INVALID_REQUEST, 
                    status=400, 
                    errors=dict(time_serializer.errors)
                ).get_response()
            time_from = time_serializer.validated_data['date_from']  # type: ignore
            time_to = time_serializer.validated_data['date_to'] # type: ignore
        elif r_time_to is not None:
            serializer = TimestampSerializer(data = {'timestamp': r_time_to})
            if not serializer.is_valid():
                L.error(f"Date {r_time_to}; {dict(serializer.errors)}")
                return ProblemJSONResponse(
                    ProblemJSONContent.INVALID_REQUEST, 
                    status=400, 
                    errors=dict(serializer.errors)
                ).get_response()
            time_to = time_serializer.validated_data['date_from']  # type: ignore
        elif r_time_from is not None:
            serializer = TimestampSerializer(data = {'timestamp': r_time_from})
            if not serializer.is_valid():
                L.error(f"Date {r_time_from}; {dict(serializer.errors)}")
                return ProblemJSONResponse(
                    ProblemJSONContent.INVALID_REQUEST, 
                    status=400, 
                    errors=dict(serializer.errors)
                ).get_response()
            time_from = time_serializer.validated_data['date_from']  # type: ignore
            

        # Model query
        measurements = Measurement.get_measurements(from_timestamp=time_from, to_timestamp=time_to, series=series, order_by=sort, limit=limit)

        return JsonResponse(data=MeasurementSerializer(measurements, many=True).data, status=200, safe=False)

    def post(self, request):
        # Get required params
        r_x_api_key = request.headers.get('X-API-Key')
        r_value = request.data.get('value')
        r_timestamp = request.data.get('timestamp')

        # Verify required params
        if r_x_api_key is None:
            return ProblemJSONResponse(
                content=ProblemJSONContent.UNAUTHORIZED_SENSOR,
                status=401,
                errors={'X-API-Key': 'Sensor api key is required.'}
            ).get_response()

        sensor = Sensor.get_sensor_by_api_key(r_x_api_key)
        if sensor is None:
            return ProblemJSONResponse(
                        content=ProblemJSONContent.NOT_FOUND,
                        status=401,
                        errors={'X-API-Key': 'Sensor with this api key was not found.'}
                    ).get_response()

        if not isinstance(r_value, (int, float)):
            return ProblemJSONResponse(
                    content=ProblemJSONContent.INVALID_REQUEST,
                    status=400,
                    errors={'value': 'Must be numeric.'}
                ).get_response()

        series_min_val, series_max_val = sensor.series.min_value, sensor.series.max_value
        if r_value > series_max_val or r_value < series_min_val:
            L.warning(f'Values: {series_min_val}, {series_max_val}, r_value: {r_value}')
            errors = {}
            if r_value < series_min_val:
                errors['minValue'] = f'Value of this field must be larger or equal than Series minValue ({series_min_val}).'
            if r_value > series_max_val:
                errors['maxValue'] = f'Value of this field must be smaller or equal than Series minValue ({series_max_val}).'
            return ProblemJSONResponse(
                    ProblemJSONContent.INVALID_REQUEST, 
                    status=422, 
                    errors=errors
                ).get_response()

        if r_timestamp is None:
            timestamp = now()
        else:
            
            serializer = TimestampSerializer(data = {'timestamp': r_timestamp})
            if not serializer.is_valid():
                L.error(f"Date {r_timestamp}; {dict(serializer.errors)}")
                return ProblemJSONResponse(
                    ProblemJSONContent.INVALID_REQUEST, 
                    status=422, 
                    errors=dict(serializer.errors)
                ).get_response()

            timestamp = serializer.validated_data["timestamp"] # type: ignore

        measurement = Measurement.create_measurement(r_value, timestamp, sensor.pk)
        measurement_json = MeasurementSerializer(measurement).data
        return JsonResponse(measurement_json, status=201, safe=False, headers={"Location": f'/api/measurements/{measurement.pk}'})



class MeasurementSingleView(APIView):
    renderer_classes = [JSONRenderer]   # Accept other than json > 406
    parser_classes = [JSONParser]       # Content-Type other than json > 415

    def get(self, request, id):
        measurement = Measurement.get_measurement_by_id(id)
        if measurement is None:
            return ProblemJSONResponse(ProblemJSONContent.NOT_FOUND, errors={'id': 'Measurement with provided id was not found.'}, status=404).get_response()
        response = MeasurementSerializer(measurement).data
        return JsonResponse(data=response, status=200)
