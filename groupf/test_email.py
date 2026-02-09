import os
import django
from django.core.mail import send_mail
from django.conf import settings

# Django設定を読み込む
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

print("DEBUG settings:", settings.DEBUG)
print("EMAIL_BACKEND:", settings.EMAIL_BACKEND)
print("EMAIL_HOST_USER:", settings.EMAIL_HOST_USER)

try:
    send_mail(
        'Test Email from Django',
        'This is a test email sent from the Django shell to verify SMTP configuration.',
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER], # 自分自身に送信
        fail_silently=False,
    )
    print("Email sent successfully!")
except Exception as e:
    print(f"Error sending email: {e}")
