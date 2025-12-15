from django.contrib import admin
from django.urls import path
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('atualizar_valores', views.atualizar_valores, name='atualizar_valores'),
    
    path('comando/<str:comando>', views.comando_spotify, name='comando_spotify'),
    
    path('adicionar_nota', views.adicionar_nota, name='adicionar_nota'),
    path('deletar_nota/<int:nota_id>', views.deletar_nota, name='deletar_nota'),
]