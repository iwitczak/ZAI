from django.urls import path
import accounts.views as v

urlpatterns = [
    # path('health/', v.check_health, name='api_health'),
    path('login', v.login, name='accounts_login'),
    path('logout', v.logout, name='accounts_logout'),
    path('password', v.change_password, name='accounts_change_password'),
]