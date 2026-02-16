from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User, PhoneOTP, ContactMessage
from accounts.serializers import (
    OTPStartSerializer,
    OTPVerifySerializer,
    UserReadSerializer,
    UserUpdateSerializer,
    AdminUserReadSerializer,
    AdminUserUpdateSerializer,
    ContactMessageCreateSerializer,
    ContactMessageReadSerializer,
)
from .permission import IsStaff
from .utils import issue_otp


class AuthStartView(generics.GenericAPIView):
    """
    Start auth by phone number (register or login) and send an OTP.

    Behavior:
      - Creates the user if it does not exist.
      - Sends OTP to the phone if the user is active.

    Input (JSON):
      - phone: string (11 digits)

    Responses:
      - 200 OK: {"detail": "OTP sent"}
      - 403 Forbidden: user is disabled
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = OTPStartSerializer

    def post(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        phone = s.validated_data["phone"]
        user, _ = User.objects.get_or_create(phone=phone, defaults={"is_active": True})

        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        issue_otp(phone=phone)
        return Response({"detail": "OTP sent"}, status=status.HTTP_200_OK)


class AuthVerifyView(generics.GenericAPIView):
    """
    Verify OTP and issue JWT tokens.

    Input (JSON):
      - phone: string (11 digits)
      - code: string (5-6 chars)

    Responses:
      - 200 OK: {"refresh": "...", "access": "..."}
      - 400 Bad Request: expired OTP / invalid OTP / validation error
      - 403 Forbidden: user is disabled
      - 404 Not Found: OTP not found / user not found
      - 429 Too Many Requests: no attempts left
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
        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
        print('nima')
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
      - 200 OK: current user profile

    PATCH/PUT Input (JSON):
      - email?: string
      - full_name?: string
      - national_id?: string
      - city?: string
      - address?: string

    PATCH/PUT Responses:
      - 200 OK: updated profile
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


class UserListView(generics.ListAPIView):
    """
    List users for admin panel.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_staff == True

    Responses:
      - 200 OK: paginated list (if pagination enabled)
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not staff
    """

    permission_classes = (IsStaff,)
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserReadSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a user (admin only).

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_staff == True

    URL params:
      - pk: int (User ID)

    GET Response:
      - 200 OK: user data
      - 404 Not Found: user not found

    PATCH/PUT Input (JSON):
      - email?: string
      - full_name?: string
      - national_id?: string
      - city?: string
      - address?: string
      - is_active?: bool
      - is_admin?: bool

    Responses:
      - 200 OK: updated user
      - 204 No Content: user deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not staff
      - 404 Not Found: user not found
    """

    permission_classes = (IsStaff,)
    queryset = User.objects.all()
    serializer_class = AdminUserUpdateSerializer


class ContactMessageCreateView(generics.CreateAPIView):
    """
    Create a contact message.

    Input (JSON):
      - name: string
      - phone: string
      - message: string

    Notes:
      - client_info is auto-filled from IP and User-Agent.

    Responses:
      - 201 Created: created message
      - 400 Bad Request: validation error
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ContactMessageCreateSerializer

    def perform_create(self, serializer):
        meta = self.request.META
        forwarded = meta.get("HTTP_X_FORWARDED_FOR")
        ip = forwarded.split(",")[0].strip() if forwarded else meta.get("REMOTE_ADDR")
        user_agent = meta.get("HTTP_USER_AGENT", "")
        client_info = f"ip={ip}; ua={user_agent}"
        serializer.save(client_info=client_info)


class AdminContactMessageListView(generics.ListAPIView):
    """
    Admin list contact messages.

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_staff == True

    Responses:
      - 200 OK: list of contact messages (newest first)
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not staff
    """

    permission_classes = (IsStaff,)
    serializer_class = ContactMessageReadSerializer

    def get_queryset(self):
        return ContactMessage.objects.all().order_by("-created_at")
