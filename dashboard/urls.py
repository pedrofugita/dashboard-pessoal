from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/valores/', views.atualizar_valores, name='atualizar_valores'),
]