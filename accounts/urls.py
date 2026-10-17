from django.urls import path
import accounts.views as v

urlpatterns = [
    # path('health/', v.check_health, name='api_health'),
    path('login', v.login, name='accounts_login'),
]