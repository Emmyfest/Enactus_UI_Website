from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,Permission,PermissionsMixin
from django.db import models
from django.utils import timezone
class Role(models.Model):
    """Configurable organisational role. Positions are data, not code."""
    name=models.CharField(max_length=80,unique=True); slug=models.SlugField(unique=True)
    description=models.TextField(blank=True); is_active=models.BooleanField(default=True)
    permissions=models.ManyToManyField(Permission,blank=True,related_name='roles')
    def __str__(self): return self.name
class UserManager(BaseUserManager):
    use_in_migrations=True
    def _make(self,email,password,**x):
        if not email: raise ValueError('An email address is required')
        u=self.model(email=self.normalize_email(email),**x); u.set_password(password); u.save(using=self._db); return u
    def create_user(self,email,password=None,**x):
        x.setdefault('is_staff',False); x.setdefault('is_superuser',False); return self._make(email,password,**x)
    def create_superuser(self,email,password=None,**x):
        x.update(is_staff=True,is_superuser=True,email_verified=True); return self._make(email,password,**x)
class User(AbstractBaseUser,PermissionsMixin):
    email=models.EmailField(unique=True); full_name=models.CharField(max_length=150)
    is_active=models.BooleanField(default=True); is_staff=models.BooleanField(default=False)
    email_verified=models.BooleanField(default=False); date_joined=models.DateTimeField(default=timezone.now)
    roles=models.ManyToManyField(Role,blank=True,related_name='users')
    USERNAME_FIELD='email'; REQUIRED_FIELDS=['full_name']; objects=UserManager()
    def __str__(self): return self.full_name or self.email
class LoginHistory(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='logins'); at=models.DateTimeField(auto_now_add=True)
    ip=models.GenericIPAddressField(null=True,blank=True); user_agent=models.CharField(max_length=300,blank=True)
    class Meta: ordering=['-at']
