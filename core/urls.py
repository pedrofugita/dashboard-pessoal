from django.contrib import admin
from django.urls import path, include
from dashboard import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('adicionar_nota/', views.adicionar_nota, name='adicionar_nota'),
    path('deletar_nota/<int:nota_id>/', views.deletar_nota, name='deletar_nota'),
]