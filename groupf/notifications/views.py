from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Notification

@login_required
def index(request):
    notifications = Notification.objects.filter(recipient=request.user).select_related('notification_type').order_by('-created_at')
    return render(request, 'notifications/index.html', {'notifications': notifications})
