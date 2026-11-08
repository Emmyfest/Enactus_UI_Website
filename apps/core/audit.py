from .utils import client_ip
def record(actor,action,target=None,detail='',request=None):
    from .models import AuditLog
    AuditLog.objects.create(actor=actor if getattr(actor,'pk',None) else None,action=action,target='' if target is None else str(target),
        target_id=str(getattr(target,'pk','') or ''),detail=detail,ip=client_ip(request))
