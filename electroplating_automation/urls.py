from django.urls import path
from knox import views as knox_views
from .views import TankAutomatorView
from .c_views import CraneTwoView
from .update_views import UpdateView

urlpatterns = [
    path('tanks_automator', TankAutomatorView.as_view()),
    path('crane_2', CraneTwoView.as_view()),
    #path('update', UpdateView.as_view()),
]