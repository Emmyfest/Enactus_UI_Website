from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404,render
from .models import Opportunity
def listing(request):
    qs=Opportunity.objects.filter(is_published=True); q=request.GET.get('q','').strip(); c=request.GET.get('category','')
    if q: qs=qs.filter(Q(name__icontains=q)|Q(organiser__icontains=q)|Q(description__icontains=q))
    if c: qs=qs.filter(category=c)
    items=sorted(qs,key=lambda o:(not o.is_open,o.deadline is None,o.deadline or o.created.date()))   # open first, expired never shown as open
    return render(request,'opportunities/list.html',{'items':items,'q':q,'cat':c,'cats':Opportunity.CAT})
def detail(request,pk):
    o=get_object_or_404(Opportunity,pk=pk)
    if not o.is_published and not request.user.has_perm('opportunities.change_opportunity'): raise Http404
    return render(request,'opportunities/detail.html',{'o':o})
