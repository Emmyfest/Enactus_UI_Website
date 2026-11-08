from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from apps.accounts import views as acc
from apps.core import views as core
from apps.comms import views as com
from apps.events import views as ev
from apps.executives import views as exe
from apps.impact import views as imp
from apps.projects import views as pr
from apps.members import views as mem
urlpatterns=[
 path('admin/',admin.site.urls),
 path('health/',core.health,name='health'),
 path('',core.home,name='home'),
 path('accounts/login/',acc.ThrottledLoginView.as_view(),name='login'),
 path('accounts/register/',acc.register,name='register'),
 path('accounts/verify/<str:token>/',acc.verify_email,name='verify_email'),
 path('accounts/',include('django.contrib.auth.urls')),
 path('dashboard/',acc.dashboard,name='dashboard'),
 path('join/',mem.apply,name='apply'),
 path('applications/',mem.review,name='review'),
 path('applications/<int:pk>/decide/',mem.decide,name='decide'),
 path('leadership/',exe.leadership,name='leadership'),
 path('projects/',pr.project_list,name='project_list'),
 path('projects/<slug:slug>/',pr.project_detail,name='project_detail'),
 path('projects/<slug:slug>/tasks/add/',pr.task_add,name='task_add'),
 path('tasks/<int:pk>/status/',pr.task_status,name='task_status'),
 path('events/',ev.event_list,name='event_list'),
 path('events/<slug:slug>/',ev.event_detail,name='event_detail'),
 path('events/<slug:slug>/register/',ev.register,name='event_register'),
 path('events/<slug:slug>/checkin/',ev.checkin,name='checkin'),
 path('events/<slug:slug>/attendance/<int:pk>/remove/',ev.remove_attendance,name='attendance_remove'),
 path('events/<slug:slug>/attendance.csv',ev.attendance_csv,name='attendance_csv'),
 path('impact/',imp.dashboard,name='impact'),
 path('impact/review/',imp.review_queue,name='impact_queue'),
 path('impact/projects/<slug:slug>/records/new/',imp.record_new,name='impact_new'),
 path('impact/records/<int:pk>/',imp.record_detail,name='impact_record'),
 path('impact/records/<int:pk>/edit/',imp.record_edit,name='impact_edit'),
 path('impact/records/<int:pk>/action/',imp.record_action,name='impact_action'),
 path('impact/records/<int:pk>/evidence/',imp.evidence_add,name='impact_evidence'),
 path('impact/projects/<slug:slug>/reports/new/',imp.report_new,name='report_new'),
 path('impact/reports/<int:pk>/',imp.report_detail,name='report_detail'),
 path('impact/reports/<int:pk>/action/',imp.report_action,name='report_action'),
 path('news/',com.announcements,name='news'),
 path('news/new/',com.announce,name='announce'),
 path('notifications/',com.notifications,name='notifications'),
 path('notifications/read/',com.mark_read,name='mark_all_read'),
 path('notifications/<int:pk>/read/',com.mark_read,name='mark_read'),
]
if settings.DEBUG: urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
