# groupf/groupf/urls.py

#aaaaaああ
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tasks.urls')),
    path('', include('accounts.urls')),
    path('manuals/', include('manuals.urls')),
    path('consultations/', include('consultations.urls')),
    path('interviews/', include('interviews.urls')),
    path('schedule/', include('schedule.urls')),
    path('notifications/', include('notifications.urls')),
    path('chat/', include('chat.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()