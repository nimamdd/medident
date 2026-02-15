from rest_framework import serializers
from accounts.models import User, ContactMessage


class OTPStartSerializer(serializers.Serializer):
    phone = serializers.CharField(min_length=11, max_length=11)


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(min_length=11, max_length=11)
    code = serializers.CharField(min_length=5, max_length=6)


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "email", "full_name", "national_id", "city", "address", "date_joined")
        read_only_fields = ("id", "phone", "date_joined")


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "full_name", "national_id", "city", "address")


class AdminUserReadSerializer(UserReadSerializer):
    class Meta(UserReadSerializer.Meta):
        fields = UserReadSerializer.Meta.fields + ("is_active", "is_admin")


class AdminUserUpdateSerializer(UserUpdateSerializer):
    class Meta(UserUpdateSerializer.Meta):
        fields = UserUpdateSerializer.Meta.fields + ("is_active", "is_admin")


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ("name", "phone", "message")


class ContactMessageReadSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ContactMessage
        fields = ("id", "name", "phone", "message", "client_info", "createdAt")
        read_only_fields = ("id", "createdAt")
