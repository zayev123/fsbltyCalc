from django.urls import path
from knox import views as knox_views
from . import views

urlpatterns = [
    path('tanks_automator', views.TankAutomatorView.as_view()),
]