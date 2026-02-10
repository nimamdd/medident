from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, PhoneOTP
from accounts.serializers import (
    RegisterSerializer,
    LoginStartSerializer,
    OTPVerifySerializer,
    PasswordResetStartSerializer,
    PasswordResetVerifySerializer,
    UserReadSerializer,
    UserUpdateSerializer,
    AdminUserReadSerializer,
    AdminUserUpdateSerializer,
)
from .permission import IsStaff
from .utils import issue_otp


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user.

    Input (JSON):
      - phone: string (10 digits)
      - password: string (min length: 5)
      - first_name: string (optional)
      - last_name: string (optional)
      - email: string (optional)

    Responses:
      - 201 Created: user created successfully
      - 400 Bad Request: validation error (e.g. phone exists / invalid phone / weak password)
    """

    serializer_class = RegisterSerializer
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)


class LoginStartView(generics.GenericAPIView):
    """
    Start login by verifying credentials and sending an OTP.

    Input (JSON):
      - phone: string
      - password: string

    Responses:
      - 200 OK: OTP sent
      - 401 Unauthorized: invalid credentials
      - 403 Forbidden: user is disabled
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginStartSerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = s.validated_data["phone"]
        password = s.validated_data["password"]

        user = authenticate(username=phone, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        issue_otp(phone=phone)
        return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)


class LoginVerifyView(generics.GenericAPIView):
    """
    Verify OTP and issue JWT tokens.

    Input (JSON):
      - phone: string
      - code: string (OTP)

    Responses:
      - 200 OK: returns access and refresh tokens
      - 400 Bad Request: expired OTP / invalid OTP
      - 404 Not Found: OTP not found / user not found
      - 429 Too Many Requests: no attempts left
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = OTPVerifySerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = s.validated_data["phone"]
        code = s.validated_data["code"]

        otp = PhoneOTP.objects.filter(phone=phone, used=False).order_by("-created_at").first()
        if not otp:
            return Response({"detail": "OTP not found"}, status=status.HTTP_404_NOT_FOUND)

        if otp.is_expired():
            return Response({"detail": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        if otp.attempts_left == 0:
            return Response({"detail": "No attempts left"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if otp.code != code:
            otp.attempts_left -= 1
            otp.save(update_fields=["attempts_left"])
            return Response({"detail": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        otp.used = True
        otp.save(update_fields=["used"])

        user = get_object_or_404(User, phone=phone)
        refresh = RefreshToken.for_user(user)

        return Response(
            {"refresh": str(refresh), "access": str(refresh.access_token)},
            status=status.HTTP_200_OK,
        )


class PasswordResetStartView(generics.GenericAPIView):
    """
    Start password reset by sending an OTP to the phone.

    Input (JSON):
      - phone: string

    Responses:
      - 200 OK: OTP sent
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetStartSerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = s.validated_data["phone"]
        issue_otp(phone=phone)
        return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)


class PasswordResetVerifyView(generics.GenericAPIView):
    """
    Verify OTP, set a new password, and issue JWT tokens.

    Input (JSON):
      - phone: string
      - code: string (OTP)
      - new_password: string

    Responses:
      - 200 OK: password changed and returns access and refresh tokens
      - 400 Bad Request: expired OTP / invalid OTP / weak password
      - 404 Not Found: OTP not found / user not found
      - 429 Too Many Requests: no attempts left
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = PasswordResetVerifySerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = s.validated_data["phone"]
        code = s.validated_data["code"]
        new_password = s.validated_data["new_password"]

        otp = PhoneOTP.objects.filter(phone=phone, used=False).order_by("-created_at").first()
        if not otp:
            return Response({"detail": "OTP not found"}, status=status.HTTP_404_NOT_FOUND)

        if otp.is_expired():
            return Response({"detail": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        if otp.attempts_left == 0:
            return Response({"detail": "No attempts left"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if otp.code != code:
            otp.attempts_left -= 1
            otp.save(update_fields=["attempts_left"])
            return Response({"detail": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        otp.used = True
        otp.save(update_fields=["used"])

        user = get_object_or_404(User, phone=phone)
        user.set_password(new_password)
        user.save(update_fields=["password"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {"refresh": str(refresh), "access": str(refresh.access_token)},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the current authenticated user's profile.

    Auth:
      - Requires: Authorization: Bearer <access_token>

    GET Response:
      - 200 OK: returns the current user's profile

    PATCH/PUT Input (JSON):
      - first_name: string (optional)
      - last_name: string (optional)
      - email: string (optional)

    PATCH/PUT Responses:
      - 200 OK: returns updated profile
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
    """

    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserReadSerializer


class AdminUserListView(generics.ListAPIView):
    """
    List users for admin panel.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_staff == True

    Query params:
      - page: int (optional, if pagination is enabled)
      - q: string (optional, if you implement search)

    Responses:
      - 200 OK: paginated list (or full list) of users
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not staff
    """

    permission_classes = (IsStaff,)
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserReadSerializer


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update a user (admin only).

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_staff == True

    URL params:
      - pk: int (User ID)

    GET Response:
      - 200 OK: returns the user data
      - 404 Not Found: user not found

    PATCH/PUT Input (JSON):
      - first_name: string (optional)
      - last_name: string (optional)
      - email: string (optional)
      - is_active: bool (optional)
      - is_staff: bool (optional)

    PATCH/PUT Responses:
      - 200 OK: returns updated user
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not staff
      - 404 Not Found: user not found
    """

    permission_classes = (IsStaff,)
    queryset = User.objects.all()
    serializer_class = AdminUserUpdateSerializer