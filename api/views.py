from django.shortcuts import render
from django.http import JsonResponse

def check_health(request):
    if request.method == 'GET':
        data = {'status': 'ok'}
        return JsonResponse(data)
    else:
        return 


