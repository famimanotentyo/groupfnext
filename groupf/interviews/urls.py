from django.urls import path
from . import views

urlpatterns = [
    path('', views.interview_home, name='interview_home'),
    path('create/', views.interview_create, name='interview_create'),
    path('detail/<int:pk>/', views.interview_detail, name='interview_detail'),
    path('feedback/<int:pk>/', views.interview_feedback, name='interview_feedback'),
    path('confirm/<int:pk>/', views.interview_confirm, name='interview_confirm'),
    path('analysis/<int:pk>/', views.member_analysis, name='member_analysis'),
]
