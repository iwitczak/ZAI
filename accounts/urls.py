from django.urls import path
import accounts.views as v

urlpatterns = [
    path('login', v.LoginView.as_view(), name='accounts_login'),
    path('logout', v.LogoutView.as_view(), name='accounts_logout'),
    path('password', v.ChangePasswordView.as_view(), name='accounts_change_password'),
]