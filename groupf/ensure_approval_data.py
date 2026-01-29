
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from manuals.models import ManualStatusMaster
from notifications.models import NotificationTypeMaster

def ensure_master_data():
    # 1. ManualStatusMaster
    status, created = ManualStatusMaster.objects.get_or_create(
        code='rejected',
        defaults={'name': '却下'}
    )
    if created:
        print(f"Created ManualStatusMaster: {status}")
    else:
        print(f"Existing ManualStatusMaster: {status}")

    # 2. NotificationTypeMaster
    notif_type, created = NotificationTypeMaster.objects.get_or_create(
        code='manual_reject',
        defaults={'name': 'マニュアル却下'}
    )
    if created:
        print(f"Created NotificationTypeMaster: {notif_type}")
    else:
        print(f"Existing NotificationTypeMaster: {notif_type}")

if __name__ == '__main__':
    ensure_master_data()
