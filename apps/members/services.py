from django.utils import timezone
from apps.comms.notify import notify
from apps.core.audit import record
from .models import Application,MemberProfile
def activate_membership(a,request=None):
    """Create a probationary membership for an accepted applicant who has a VERIFIED account with the same email."""
    from apps.accounts.models import User
    u=User.objects.filter(email__iexact=a.email,email_verified=True).first()
    if not u or hasattr(u,'member_profile'): return None
    m=a.matric_number if a.matric_number and not MemberProfile.objects.filter(matric_number=a.matric_number).exists() else ''
    p=MemberProfile.objects.create(user=u,status='probationary',matric_number=m,phone=a.phone,faculty=a.faculty,department=a.department,level=a.level,skills=a.skills,joined=timezone.localdate())
    record(None,'member.activated',p,a.reference,request=request); notify(u,'Your Enactus UI membership is active (probationary). Welcome!','/dashboard/'); return p
def link_accepted(user):
    a=Application.objects.filter(email__iexact=user.email,status='accepted').order_by('-created').first()
    return activate_membership(a) if a else None
