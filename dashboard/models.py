from django.db import models

class Anotacao(models.Model):
    texto = models.CharField(max_length=100) # Limite de 100 caracteres para caber no layout
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.texto