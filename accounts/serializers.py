from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Create a new user with phone and password."""

    password = serializers.CharField(write_only=True, min_length=5)

    class Meta:
        model = User
        fields = ("phone", "password", "first_name", "last_name", "email")

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginStartSerializer(serializers.Serializer):
    """Validate phone and password for login start."""

    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)


class OTPVerifySerializer(serializers.Serializer):
    """Validate phone and OTP code."""

    phone = serializers.CharField()
    code = serializers.CharField(min_length=5, max_length=6)


class PasswordResetStartSerializer(serializers.Serializer):
    """Validate phone for password reset start."""

    phone = serializers.CharField()


class PasswordResetVerifySerializer(OTPVerifySerializer):
    """Validate OTP and set a new password."""

    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class UserReadSerializer(serializers.ModelSerializer):
    """Read-only user profile data."""

    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "email", "date_joined")
        read_only_fields = ("id", "phone", "date_joined")


class UserUpdateSerializer(serializers.ModelSerializer):
    """Update the current user's profile fields."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class AdminUserReadSerializer(UserReadSerializer):
    """Read user data for admin views."""

    class Meta(UserReadSerializer.Meta):
        fields = UserReadSerializer.Meta.fields + ("is_active", "is_staff")


class AdminUserUpdateSerializer(UserUpdateSerializer):
    """Update user fields as an admin."""

    class Meta(UserUpdateSerializer.Meta):
        fields = UserUpdateSerializer.Meta.fields + ("is_active", "is_staff")