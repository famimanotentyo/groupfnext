from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='schedule_index'),
    path('events/', views.get_events, name='schedule_get_events'),
    path('add/', views.add_event, name='schedule_add_event'),
]
