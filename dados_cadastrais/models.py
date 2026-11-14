from django.db import models

<<<<<<< HEAD
class Vendedor(models.Model):
    vendedor_nome = models.CharField(max_length=100)

    def str__(self):
        return self.vendedor_nome

=======

class Vendedor(models.Model):
    vendedor_nome = models.CharField(max_length=100)

    def __str__(self):
        return self.vendedor_nome


>>>>>>> 6ed6c6a (Primeiro Commit)
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

<<<<<<< HEAD
    def str__(self):
            return self.razao_social
    
=======
    def __str__(self):
        return self.razao_social

>>>>>>> 6ed6c6a (Primeiro Commit)
