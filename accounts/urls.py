from django.urls import path
from accounts.views import *

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/start/', LoginStartView.as_view(), name='login_start'),
    path('login/verify/', LoginVerifyView.as_view(), name='login_verify'),
    path("password/reset/start/", PasswordResetStartView.as_view()),
    path("password/reset/verify/", PasswordResetVerifyView.as_view()),
    path("me/", MeView.as_view(), name="me"),

]
