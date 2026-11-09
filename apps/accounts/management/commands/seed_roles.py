from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.accounts.models import Role
OPS=['academy.manage_academy','academy.issue_certificate','partnerships.manage_partnerships','executives.prepare_handover','executives.manage_transition','members.export_members','documents.add_document','documents.change_document','finance.view_finance','impact.review_report','events.manage_attendance','comms.add_announcement','projects.change_project','projects.view_project']
REVIEW=['members.review_application','members.view_application','members.view_memberprofile']
ROLES={'Super Administrator':[],'Website Administrator':['core.manage_media','core.view_sitesetting','core.add_sitesetting','core.change_sitesetting'],
'Team Lead':OPS+REVIEW+['executives.view_administration','executives.view_appointment'],'Deputy Team Lead':OPS+['executives.accept_handover']+REVIEW+['executives.view_administration','executives.view_appointment'],
'Secretary General':REVIEW+['partnerships.manage_partnerships','executives.accept_handover','events.manage_attendance','comms.add_announcement','members.export_members','members.view_sensitive','documents.add_document','documents.change_document'],'Financial Secretary':['finance.view_finance','finance.record_finance'],'Treasurer':['finance.view_finance','finance.approve_finance'],'Project Manager':[],'Departmental Executive':[],'Active Member':[],'Probationary Member':[],'Alumni':[],'Faculty Advisor':['impact.verify_impact','impact.review_report','projects.view_project'],'External Partner':[],'Prospective Member':[]}
class Command(BaseCommand):
    help='Create or update the default roles (safe to run repeatedly). Edit permissions afterwards in the admin.'
    def handle(self,*a,**k):
        for name,perms in ROLES.items():
            r,_=Role.objects.get_or_create(slug=slugify(name),defaults={'name':name})
            for p in perms:
                app,code=p.split('.'); obj=Permission.objects.filter(content_type__app_label=app,codename=code).first()
                if obj: r.permissions.add(obj)
        self.stdout.write(self.style.SUCCESS(f'{len(ROLES)} roles ready'))
