from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('study-sessions/', views.study_sessions_view, name='study_sessions'),
    path('resources/', views.resources_view, name='resources'),
    path('about/', views.about_view, name='about'),
    path('timer/', views.timer_page, name='timer'),
]