from django.db import models

class Vendedor(models.Model):
    vendedor_nome = models.CharField(max_length=100)

    def str__(self):
        return self.vendedor_nome

class Cliente(models.Model):
    razao_social = models.CharField(max_length=100)
    cnpj = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=11, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    bairro_informado = models.CharField(max_length=100)
    cep = models.CharField(max_length=8)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    vendedor_id = models.ForeignKey(Vendedor, on_delete=models.CASCADE)

    def str__(self):
            return self.razao_social_nome
    