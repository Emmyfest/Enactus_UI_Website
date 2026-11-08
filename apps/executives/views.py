from django.shortcuts import render
from .models import Administration
def leadership(request):
    cur=Administration.objects.filter(is_current=True).first()
    appts=cur.appointments.filter(is_public=True).select_related('user','position') if cur else []
    return render(request,'executives/leadership.html',{'admin_term':cur,'appts':appts})
