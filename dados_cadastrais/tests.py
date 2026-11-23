"""Testes mínimos da persistência ETL, isolados do contrato público da API."""
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase

from .models import AuditoriaETL, Cliente, Vendedor


class IntegracaoETLTests(TestCase):
    def test_conferencia_nao_grava_no_banco(self):
        with TemporaryDirectory() as pasta:
            call_command("importar_etl", "--saida", pasta)
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertEqual(AuditoriaETL.objects.count(), 0)

    def test_importacao_valores_tratados_originais_e_auditoria(self):
        with TemporaryDirectory() as pasta:
            call_command("importar_etl", "--saida", pasta, "--persistir")
        self.assertEqual(Cliente.objects.count(), 47)
        self.assertEqual(Vendedor.objects.count(), 5)
        self.assertEqual(AuditoriaETL.objects.count(), 217)
        cliente = Cliente.objects.get(id_cliente="CLI0002")
        self.assertEqual(cliente.bairro_informado, "Águas Claras")
        self.assertEqual(cliente.bairro_informado_original, "Sul (Aguas Claras)")
        self.assertEqual(cliente.cep, "72140-010")
        self.assertTrue(Cliente.objects.filter(necessita_revisao=True).exists())

    def test_reimportacao_nao_duplica_clientes(self):
        with TemporaryDirectory() as pasta:
            call_command("importar_etl", "--saida", pasta, "--persistir")
            call_command("importar_etl", "--saida", pasta, "--persistir")
        self.assertEqual(Cliente.objects.count(), 47)
        self.assertEqual(Vendedor.objects.count(), 5)
        self.assertEqual(AuditoriaETL.objects.count(), 434)

    def test_admin_auditoria_nao_permita_alteracoes(self):
        audit_admin = admin.site._registry[AuditoriaETL]
        self.assertFalse(audit_admin.has_add_permission(None))
        self.assertFalse(audit_admin.has_change_permission(None))
        self.assertFalse(audit_admin.has_delete_permission(None))
