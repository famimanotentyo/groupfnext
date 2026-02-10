
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from accounts.models import RoleMaster
from tasks.models import TaskStatusMaster, TaskTypeMaster
from manuals.models import ManualStatusMaster, ManualVisibilityMaster
from consultations.models import ConsultationStatusMaster
from schedule.models import ScheduleEventTypeMaster
from interviews.models import InterviewStatusMaster
from notifications.models import NotificationTypeMaster

print("--- RoleMaster ---")
for r in RoleMaster.objects.all():
    print(f"Code: {r.code}, Name: {r.name}")

print("\n--- TaskStatusMaster ---")
for s in TaskStatusMaster.objects.all():
    print(f"Code: {s.code}, Name: {s.name}")

print("\n--- TaskTypeMaster ---")
for t in TaskTypeMaster.objects.all():
    print(f"Code: {t.code}, Name: {t.name}")

print("\n--- ManualStatusMaster ---")
for s in ManualStatusMaster.objects.all():
    print(f"Code: {s.code}, Name: {s.name}")

print("\n--- ManualVisibilityMaster ---")
for v in ManualVisibilityMaster.objects.all():
    print(f"Code: {v.code}, Name: {v.name}")

print("\n--- ConsultationStatusMaster ---")
for s in ConsultationStatusMaster.objects.all():
    print(f"Code: {s.code}, Name: {s.name}")

print("\n--- ScheduleEventTypeMaster ---")
for s in ScheduleEventTypeMaster.objects.all():
    print(f"Code: {s.code}, Name: {s.name}")

print("\n--- InterviewStatusMaster ---")
for s in InterviewStatusMaster.objects.all():
    print(f"Code: {s.code}, Name: {s.name}")

print("\n--- NotificationTypeMaster ---")
for notif in NotificationTypeMaster.objects.all():
    print(f"Code: {notif.code}, Name: {notif.name}")
