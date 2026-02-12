from datetime import timedelta
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone, **extra_fields):
        if not phone:
            raise ValueError("Phone is required")
        user = self.model(phone=phone, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_admin", True)
        return self.create_user(phone, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(
        max_length=11,
        unique=True,
        validators=[RegexValidator(regex=r"^\d{11}$", message="Phone number must be 11 digits")],
    )
    email = models.EmailField(blank=True, null=True)

    full_name = models.CharField(max_length=255, blank=True)
    national_id = models.CharField(max_length=10, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone


class PhoneOTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(
        max_length=11,
        db_index=True,
        validators=[RegexValidator(regex=r"^\d{11}$", message="Phone number must be 11 digits")],
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts_left = models.PositiveSmallIntegerField(default=5)
    used = models.BooleanField(default=False)

    @classmethod
    def create_for_phone(cls, phone: str, ttl_minutes: int = 2):
        cls.objects.filter(phone=phone, used=False, expires_at__gte=timezone.now()).update(used=True)
        otp = cls.objects.create(
            phone=phone,
            code="000000",
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return otp

    def is_expired(self):
        return timezone.now() >= self.expires_at