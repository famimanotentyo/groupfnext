
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from manuals.models import ManualStatusMaster
from notifications.models import NotificationTypeMaster

print("--- ManualStatusMaster ---")
for status in ManualStatusMaster.objects.all():
    print(f"Code: {status.code}, Name: {status.name}")

print("\n--- NotificationTypeMaster ---")
for notif in NotificationTypeMaster.objects.all():
    print(f"Code: {notif.code}, Name: {notif.name}")
