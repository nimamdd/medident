from django.urls import path

from accounts.views import AuthStartView, AuthVerifyView, MeView, AdminUserListView, AdminUserDetailView

urlpatterns = [
    path("auth/start/", AuthStartView.as_view()),
    path("auth/verify/", AuthVerifyView.as_view()),
    path("me/", MeView.as_view()),
    path("admin/users/", AdminUserListView.as_view()),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view()),
]
