from django.urls import path
from . import views

urlpatterns = [
    path('', views.consultation_list_view, name='consultation_list_view'),
    path('create/', views.consultation_create_view, name='consultation_create_view'),
    path('<int:pk>/', views.consultation_detail_view, name='consultation_detail_view'),
    path('<int:pk>/resolve/', views.consultation_resolve, name='consultation_resolve'),
]
