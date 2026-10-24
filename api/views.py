from django.shortcuts import render
from django.http import JsonResponse
from django.views import View


class HealthView(View):
    def get(self, request):
        data = {'status': 'ok'}
        return JsonResponse(data)

# *** SERIES ***
class SeriesView(View):
    def get(self, request):
        pass

    def post(self, request):
        pass


class SeriesSingleView(View):
    def get(self, request):
        pass

    def put(self, request):
        pass

    def delete(self, request):
        pass


# *** MEASUREMENTS ***
class MeasurementView(View):
    def get(self, request):
        pass

    def post(self, request):
        pass


class MeasurementSingleView(View):
    def get(self, request):
        pass


# *** SENSORS ***
class SensorView(View):
    def get(self, request):
        pass

    def post(self, request):
        pass


class SensorSingleView(View):
    def get(self, request):
        pass

    def delete(self, request):
        pass