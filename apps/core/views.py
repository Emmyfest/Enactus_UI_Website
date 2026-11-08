from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from .models import setting
def health(request):
    try:
        with connection.cursor() as c: c.execute('SELECT 1')
        return JsonResponse({'status':'ok'})
    except Exception: return JsonResponse({'status':'unavailable'},status=503)
def home(request):
    return render(request,'home.html',{k:setting(k) for k in ('about','mission','vision')}|{'contact_email':setting('contact_email','')})
