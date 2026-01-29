
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from interviews.models import InterviewStatusMaster
from notifications.models import NotificationTypeMaster

def ensure_interview_master_data():
    # 1. InterviewStatusMaster
    status, created = InterviewStatusMaster.objects.get_or_create(
        code='declined',
        defaults={'name': '却下・辞退'}
    )
    if created:
        print(f"Created InterviewStatusMaster: {status}")
    else:
        print(f"Existing InterviewStatusMaster: {status}")

    # 2. NotificationTypeMaster
    notif_type, created = NotificationTypeMaster.objects.get_or_create(
        code='interview_decline',
        defaults={'name': '面談辞退'}
    )
    if created:
        print(f"Created NotificationTypeMaster: {notif_type}")
    else:
        print(f"Existing NotificationTypeMaster: {notif_type}")

if __name__ == '__main__':
    ensure_interview_master_data()
