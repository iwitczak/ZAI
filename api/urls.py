from django.urls import path
import api.views as v

urlpatterns = [
    path('health/', v.check_health, name='api_health'),
]