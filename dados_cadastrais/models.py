"""Modelos propostos para a integração Primora (revisão obrigatória de migração)."""
from django.db import models


class Vendedor(models.Model):
    vendedor_nome = models.CharField(max_length=100)

    def __str__(self):
        return self.vendedor_nome


class Cliente(models.Model):
    # Identificador do CSV. Nulo permite CRUD manual com PK do Django.
    id_cliente = models.CharField(max_length=24, unique=True, null=True, blank=True)
    razao_social = models.CharField(max_length=255)

    # Campos de negócio: valores tratados, com nomes do CSV.
    cnpj = models.CharField(max_length=18, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    bairro_informado = models.CharField(max_length=100, null=True, blank=True)
    cep = models.CharField(max_length=9, null=True, blank=True)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    data_cadastro = models.DateField(null=True, blank=True)
    vendedor_id = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name="clientes")

    # Campos de origem preservados para rastreabilidade.
    cnpj_original = models.CharField(max_length=100, blank=True)
    telefone_original = models.CharField(max_length=100, blank=True)
    email_original = models.CharField(max_length=254, blank=True)
    bairro_informado_original = models.CharField(max_length=100, blank=True)
    cep_original = models.CharField(max_length=100, blank=True)
    data_cadastro_original = models.CharField(max_length=100, blank=True)

    # Qualidade e consulta externa (somente interno/admin).
    bairro_via_cep = models.CharField(max_length=100, null=True, blank=True)
    status_cep = models.CharField(max_length=32, blank=True)
    status_consistencia = models.CharField(max_length=32, blank=True)
    cep_confirmado_via_cep = models.BooleanField(default=False)
    necessita_revisao = models.BooleanField(default=False)
    motivos_pendencia = models.TextField(blank=True)

    def __str__(self):
        return f"{self.id_cliente or self.pk} — {self.razao_social}"


class AuditoriaETL(models.Model):
    execucao_id = models.CharField(max_length=36, db_index=True)
    id_cliente = models.CharField(max_length=24, db_index=True)
    campo = models.CharField(max_length=100)
    valor_original = models.TextField(blank=True)
    valor_tratado = models.TextField(blank=True)
    criterio = models.TextField()
    fonte = models.TextField()
    status = models.CharField(max_length=40)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Auditorias ETL"

    def __str__(self):
        return f"{self.id_cliente}: {self.campo} ({self.status})"
