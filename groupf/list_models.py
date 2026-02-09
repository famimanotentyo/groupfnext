import os
import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

print("=== Django Models & Tables ===")
for model in apps.get_models():
    print(f"{model._meta.app_label}.{model.__name__} -> {model._meta.db_table}")
