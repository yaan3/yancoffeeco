from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.utils import timezone
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, first_name=None, last_name=None, username=None, password=None, phone_number=None, referral_code=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('User must have a username')

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name or '',  
            last_name=last_name or '',   
            username=username,
            phone_number=phone_number,  
            referral_code=referral_code,
            **extra_fields
        )
        user.set_password(password)    
        user.save(using=self._db)

        Wallet.objects.create(user=user)
        Referral.objects.create(user=user)

        return user

    def create_superuser(self, email, first_name=None, last_name=None, username=None, password=None, phone_number=None, **extra_fields):
        user = self.create_user(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            phone_number=phone_number,
            **extra_fields
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superadmin = True
        user.is_active = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=50, unique=True, null=True, blank=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)

    is_blocked = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    objects = UserManager()

    groups = models.ManyToManyField(Group, blank=True, related_name='account_user_groups')
    user_permissions = models.ManyToManyField(Permission, blank=True, related_name='account_user_permissions')

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dp_img = models.ImageField(upload_to='image', blank=True, null=True)
    bio = models.CharField(max_length=220, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.street_address}, {self.city}, {self.state} - {self.postal_code}"

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Wallet'

    def __str__(self):
        return self.user.email

class WalletHistory(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(null=True, blank=True, max_length=20)
    created_at = models.DateTimeField(default=timezone.now)
    amount = models.IntegerField(null=True)
    reason = models.CharField(null=True, blank=True, max_length=200)


class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sent_referrals', default='')
    my_referral = models.TextField(default=uuid.uuid4, blank=True)
    reffered_code = models.CharField(max_length=200, null=True, blank=True, default='')

    def __str__(self):
        return f"{self.user.username}"