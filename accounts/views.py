from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view



@api_view(['POST'])
def login(request):
    error_response = Response({'error': 'Invalid request'}, status=400)
    if request.method == 'POST':
        if not request.data:
            return error_response
        try:
            username = request.data.get('username')
            password = request.data.get('password')
        except KeyError:
            return error_response
        if isinstance(username, str) and isinstance(password, str):
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            if user is not None:
                from .models import AccessToken
                token, expires_in = AccessToken.generate_token(user)
                return Response({'token': token, 'expires_in': expires_in})
        return error_response