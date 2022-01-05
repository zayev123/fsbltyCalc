from django.urls import path
from knox import views as knox_views
from .views import TankAutomatorView
from .c_views import CraneFiveView, CraneTwoView, CraneThreeView, CraneFourView
from .update_views import UpdateView

urlpatterns = [
    path('tanks_automator', TankAutomatorView.as_view()),
    path('crane_2', CraneTwoView.as_view()),
    path('crane_3', CraneThreeView.as_view()),
    path('crane_4', CraneFourView.as_view()),
    path('crane_5', CraneFiveView.as_view()),
    #path('update', UpdateView.as_view()),
]