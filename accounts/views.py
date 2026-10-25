from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AccessToken

from utils.common_classes import *
from utils.wrappers import auth_required



class LoginView(APIView):
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if username is None or password is None:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'username': 'This field is required.', 'password': 'This field is required.'}).get_response()
        
        if isinstance(username, str) and isinstance(password, str):
            from django.contrib.auth import authenticate
            user = authenticate(request, username=username, password=password)
            if user is None:
                return ProblemJSONResponse(ProblemJSONContent.INVALID_CREDENTIALS, status=401).get_response()
            
            token, expires_in = AccessToken.generate_token(user)
            return Response({'accessToken': token, 'expiresIn': expires_in, 'tokenType': 'Bearer'}) 
        else:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'username': 'This field is required as string.', 'password': 'This field is required as string.'}).get_response()


class LogoutView(APIView):
    @auth_required
    def post(self, request):
        AccessToken.objects.filter(id=request.auth.pk).update(revoked_at=timezone.now())
        return Response(status=204)


class ChangePasswordView(APIView):
    @auth_required
    def put(self, request):
        current_user = request.user

        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')
            
        if not isinstance(current_password, str) or not isinstance(new_password, str):
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=400, errors={'currentPassword': 'This field is required as string.', 'newPassword': 'This field is required as string.'}).get_response()

        if len(new_password) < 8 or len(new_password) > 128:
            return ProblemJSONResponse(ProblemJSONContent.INVALID_REQUEST, status=422, errors={'newPassword': 'Provided new password must be between 8 and 128 characters long.'}).get_response()

        if not current_user.check_password(current_password):
            return ProblemJSONResponse(ProblemJSONContent.INVALID_CREDENTIALS, status=403, errors={'currentPassword': 'The provided current password is invalid.'}).get_response()
        
        current_user.set_password(new_password)
        current_user.save() 

        # Logout user from all sessions (invalidate all tokens)
        AccessToken.objects.filter(user__username=current_user, revoked_at__isnull=True).update(revoked_at=timezone.now())

        return Response(status=204)