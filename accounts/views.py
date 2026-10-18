from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view

from accounts.models import AccessToken

from utils.common_classes import *



@api_view(['POST'])
def login(request):
    # TODO: Dostosowanie do kontraktu api - komunikaty błędów
    if request.method == 'POST':
        try:
            username = request.data.get('username')
            password = request.data.get('password')
        except KeyError:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'username': 'This field is required.', 'password': 'This field is required.'}).get_response()
        
        if isinstance(username, str) and isinstance(password, str):
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            if user is not None:
                from .models import AccessToken
                token, expires_in = AccessToken.generate_token(user)
                return Response({'accessToken': token, 'expiresIn': expires_in, 'tokenType': 'Bearer'})
            else:
                return ProblemJSONResponse(ProblemJSONContent.INVALID_CREDENTIALS, status=401).get_response()
        else:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'username': 'This field is required as string.', 'password': 'This field is required as string.'}).get_response()       
    else:
        return ProblemJSONResponse(ProblemJSONContent.METHOD_NOT_ALLOWED, status=400).get_response()


@api_view(['POST'])
def logout(request):
    if request.method == 'POST':
        if isinstance(request.auth, AccessToken):
            AccessToken.objects.filter(id=request.auth.pk).update(revoked_at=timezone.now())
            return Response(status=204)
        else:
            return ProblemJSONResponse(ProblemJSONContent.UNAUTHORIZED, status=401).get_response()
    else:
        return ProblemJSONResponse(ProblemJSONContent.METHOD_NOT_ALLOWED, status=400).get_response()


@api_view(['PUT'])
def change_password(request):
    if request.method == 'PUT':
        if not isinstance(request.auth, AccessToken): # If not, user is not authenticated
            return ProblemJSONResponse(ProblemJSONContent.UNAUTHORIZED, status=401).get_response()

        try:
            current_user = request.user
        except Exception:
            return ProblemJSONResponse(ProblemJSONContent.UNAUTHORIZED, status=401).get_response()

        # Validate body params
        try:
            current_password = request.data.get('currentPassword')
            new_password = request.data.get('newPassword')
        except KeyError:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'currentPassword': 'This field is required.', 'newPassword': 'This field is required.'}).get_response()

        if len(new_password) < 8 or len(new_password) > 128:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=422, errors={'newPassword': 'Provided new password must be between 8 and 128 characters long.'}).get_response()

        if current_user.check_password(current_password):
            current_user.set_password(new_password)
            current_user.save()
        else:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_CREDENTIALS, status=403, errors={'currentPassword': 'The provided current password is invalid.'}).get_response()

        # Logout user from all sessions (invalidate all tokens)
        AccessToken.objects.filter(user__username=current_user, revoked_at__isnull=True).update(revoked_at=timezone.now())

        return Response(status=204)
    else:
        return ProblemJSONResponse(ProblemJSONContent.METHOD_NOT_ALLOWED, status=400).get_response()

