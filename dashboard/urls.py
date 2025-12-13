from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/valores/', views.atualizar_valores, name='atualizar_valores'),
    path('comando/<str:comando>/', views.executar_acao, name='executar_acao'),
]