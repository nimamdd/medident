from django.urls import path

from accounts.views import AuthStartView, AuthVerifyView, MeView, UserListView, UserDetailView

urlpatterns = [
    path("auth/start/", AuthStartView.as_view()),
    path("auth/verify/", AuthVerifyView.as_view()),
    path("me/", MeView.as_view()),
    path("users/", UserListView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),
]
