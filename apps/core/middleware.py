class HealthCheckMiddleware:
    """Answer /health/ before Django validates the Host header.
    Render's health check calls the instance by its internal IP, which is never in ALLOWED_HOSTS.
    Only this one path is handled here; every other URL still gets full host validation."""
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.path=='/health/' and request.method in('GET','HEAD'):
            from .views import health
            return health(request)
        return self.get_response(request)
