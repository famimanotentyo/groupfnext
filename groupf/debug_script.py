import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

try:
    print("Attempting to import schedule.views...")
    import schedule.views
    print("Import successful.")
    
    print("Attempting to execute User query in index view...")
    from accounts.models import User
    users = User.objects.filter(is_active=True).order_by('department', 'employee_number')
    print(f"User query successful. Count: {users.count()}")
    for u in users:
        print(f"User: {u}, Dept: {u.department}")
        
    print("Attempting to execute Interview query...")
    from interviews.models import Interview
    interviews = Interview.objects.all()
    print(f"Interview query successful. Count: {interviews.count()}")
    
    print("Attempting to execute ScheduleEvent query...")
    from schedule.models import ScheduleEvent
    events = ScheduleEvent.objects.all()
    print(f"ScheduleEvent query successful. Count: {events.count()}")

except Exception as e:
    print(f"ERROR DETECTED: {e}")
    import traceback
    traceback.print_exc()
