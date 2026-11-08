def client_ip(request):
    if request is None: return None
    f=request.META.get('HTTP_X_FORWARDED_FOR')
    return (f.split(',')[0].strip() if f else request.META.get('REMOTE_ADDR')) or None
