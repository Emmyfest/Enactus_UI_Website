from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect,render
from django.urls import reverse
from apps.core.audit import record
from apps.core.utils import client_ip
from .models import User
class RegisterForm(UserCreationForm):
    class Meta: model=User; fields=('email','full_name')  # roles can never be chosen at registration
class ThrottledLoginView(LoginView):
    template_name='registration/login.html'; MAX=5; WINDOW=900
    def _key(self): return f"lf:{client_ip(self.request)}:{self.request.POST.get('username','').lower()}"
    def post(self,request,*a,**k):
        if cache.get(self._key(),0)>=self.MAX: return HttpResponse('Too many failed attempts. Try again in 15 minutes.',status=429)
        return super().post(request,*a,**k)
    def form_invalid(self,form):
        k=self._key(); cache.set(k,cache.get(k,0)+1,self.WINDOW); return super().form_invalid(form)
    def form_valid(self,form):
        if settings.REQUIRE_EMAIL_VERIFICATION and not form.get_user().email_verified:
            form.add_error(None,'Please verify your email address first.'); return self.form_invalid(form)
        cache.delete(self._key()); return super().form_valid(form)
def register(request):
    form=RegisterForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        u=form.save(); record(u,'user.registered',u,request=request)
        link=request.build_absolute_uri(reverse('verify_email',args=[signing.dumps(u.pk,salt='verify')]))
        send_mail('Verify your Enactus UI account',f'Open this link to verify your email:\n{link}',None,[u.email])
        messages.success(request,'Account created. Check your email to verify it, then log in.'); return redirect('login')
    return render(request,'form.html',{'form':form,'title':'Create an account','submit':'Register'})
def verify_email(request,token):
    try: pk=signing.loads(token,salt='verify',max_age=3*86400)
    except signing.BadSignature: return render(request,'message.html',{'title':'Link invalid or expired','text':'Request a new verification email.'},status=400)
    User.objects.filter(pk=pk).update(email_verified=True)
    from apps.members.services import link_accepted
    u=User.objects.filter(pk=pk).first()
    if u: link_accepted(u)
    return render(request,'message.html',{'title':'Email verified','text':'You can now log in.'})
@login_required
def dashboard(request):
    from .dashboards import build
    return render(request,'accounts/dashboard.html',build(request.user))
