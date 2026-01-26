import os
import django
import sys

sys.path.append(r'c:\Django課題制作 - コピー\groupf')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from accounts.models import User, RoleMaster

print("Checking Roles...")
for role in RoleMaster.objects.all():
    print(f"Role: {role.code} - {role.name}")

print("\nChecking Manager Users...")
managers = User.objects.filter(role__code__in=['manager', 'admin'], is_active=True)
print(f"Count: {managers.count()}")
for u in managers:
    print(f"- {u.last_name} {u.first_name} ({u.employee_number}) Role: {u.role.code}")
