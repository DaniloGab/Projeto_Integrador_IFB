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


from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Cliente, Vendedor


class ClienteAPITestCase(APITestCase):

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="cliente_teste", password="senha_teste_123"
        )
        self.vendedor = Vendedor.objects.create(
            vendedor_nome="Vendedor Teste"
        )


        self.cliente = Cliente.objects.create(
            razao_social="Mercado Exemplo LTDA",
            cnpj="12345678000190",
            telefone="61999999999",
            email="mercado@exemplo.com",
            bairro_informado="Setor Central",
            cep="72400000",
            cidade="Gama",
            uf="DF",
            vendedor_id=self.vendedor
        )

    def test_listar_clientes(self):

        resposta = self.client.get("/api/clientes/")


        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )


        self.assertEqual(
            len(resposta.data),
            1
        )



    def test_clientes_por_vendedor(self):
        resposta = self.client.get(
            f"/api/clientes/vendedor/{self.vendedor.id}/"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(resposta.data),
            1
        )

        self.assertEqual(
            resposta.data[0]["razao_social"],
            "Mercado Exemplo LTDA"
        )



    def test_nao_listar_clientes_de_outro_vendedor(self):
        outro_vendedor = Vendedor.objects.create(
            vendedor_nome="Outro Vendedor"
        )

        Cliente.objects.create(
            razao_social="Farmacia Exemplo LTDA",
            cnpj="98765432000110",
            telefone="61888888888",
            email="farmacia@exemplo.com",
            bairro_informado="Setor Sul",
            cep="72410000",
            cidade="Gama",
            uf="DF",
            vendedor_id=outro_vendedor
        )

        resposta = self.client.get(
            f"/api/clientes/vendedor/{self.vendedor.id}/"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(resposta.data),
            1
        )

        self.assertEqual(
            resposta.data[0]["razao_social"],
            "Mercado Exemplo LTDA"
        )






    def test_consultar_cliente_por_id(self):
        resposta = self.client.get(
            f"/api/clientes/{self.cliente.id}/"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            resposta.data["razao_social"],
            "Mercado Exemplo LTDA"
        )

    def test_cadastrar_cliente(self):
        self.client.force_authenticate(user=self.usuario)
        dados = {
            "razao_social": "Cliente Novo LTDA",
            "cnpj": "11111111000111",
            "telefone": "61988887777",
            "email": "novo@exemplo.com",
            "bairro_informado": "Setor Sul",
            "cep": "72410000",
            "cidade": "Gama",
            "uf": "DF",
            "vendedor_id": self.vendedor.id
        }

        resposta = self.client.post(
            "/api/clientes/",
            dados,
            format="json"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_201_CREATED
        )

        self.assertEqual(
            Cliente.objects.count(),
            2
        )

    def test_atualizar_cliente_patch(self):
        self.client.force_authenticate(user=self.usuario)
        resposta = self.client.patch(
            f"/api/clientes/{self.cliente.id}/",
            {"razao_social": "Mercado Atualizado LTDA"},
            format="json"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.cliente.refresh_from_db()

        self.assertEqual(
            self.cliente.razao_social,
            "Mercado Atualizado LTDA"
        )

    def test_atualizar_cliente_put(self):
        self.client.force_authenticate(user=self.usuario)
        dados = {
            "razao_social": "Mercado Completo LTDA",
            "cnpj": "12345678000190",
            "telefone": "61999999999",
            "email": "mercado@exemplo.com",
            "bairro_informado": "Setor Norte",
            "cep": "72400000",
            "cidade": "Gama",
            "uf": "DF",
            "vendedor_id": self.vendedor.id
        }

        resposta = self.client.put(
            f"/api/clientes/{self.cliente.id}/",
            dados,
            format="json"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.cliente.refresh_from_db()

        self.assertEqual(
            self.cliente.bairro_informado,
            "Setor Norte"
        )

    def test_excluir_cliente(self):
        self.client.force_authenticate(user=self.usuario)
        resposta = self.client.delete(
            f"/api/clientes/{self.cliente.id}/"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_204_NO_CONTENT
        )

        self.assertFalse(
            Cliente.objects.filter(
                id=self.cliente.id
            ).exists()
        )

    def test_impedir_cnpj_duplicado(self):
        self.client.force_authenticate(user=self.usuario)
        dados = {
            "razao_social": "Outro Mercado LTDA",
            "cnpj": "12345678000190",
            "telefone": "61977776666",
            "email": "outro@exemplo.com",
            "bairro_informado": "Setor Sul",
            "cep": "72410000",
            "cidade": "Gama",
            "uf": "DF",
            "vendedor_id": self.vendedor.id
        }

        resposta = self.client.post(
            "/api/clientes/",
            dados,
            format="json"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            Cliente.objects.count(),
            1
        )


    def test_clientes_por_bairro(self):
        resposta = self.client.get(
            "/api/clientes/bairro/Setor%20Central/"
        )

        self.assertEqual(
            resposta.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            len(resposta.data),
            1
        )

        self.assertEqual(
            resposta.data[0]["bairro_informado"],
            "Setor Central"
        )



class ContratoPublicoAPITests(APITestCase):
    def setUp(self):
        self.vendedor = Vendedor.objects.create(vendedor_nome="Vendedor Público")
        self.cliente = Cliente.objects.create(
            id_cliente="CLI-EXEMPLO", razao_social="Cliente com Pendência",
            cidade="Brasília", uf="DF", vendedor_id=self.vendedor,
            bairro_informado="Águas Claras", telefone_original="(61) 9 8888-7777",
            status_cep="NAO_CONSULTADO", necessita_revisao=True,
            motivos_pendencia="Revisão necessária",
        )

    def test_api_oculta_campos_internos_e_exibe_pendencia(self):
        resposta = self.client.get(f"/api/clientes/{self.cliente.pk}/")
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["possui_pendencia"])
        for campo in ("telefone_original", "status_cep", "motivos_pendencia",
                      "necessita_revisao", "bairro_via_cep"):
            self.assertNotIn(campo, resposta.data)

    def test_get_publico_post_anonimo_bloqueado(self):
        self.assertEqual(self.client.get("/api/clientes/").status_code, status.HTTP_200_OK)
        resposta = self.client.post("/api/clientes/", {
            "razao_social": "Sem autorização", "cidade": "Brasília", "uf": "DF",
            "vendedor_id": self.vendedor.pk,
        }, format="json")
        self.assertIn(resposta.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_consulta_duas_rotas_vendedor_e_bairro(self):
        rotas = (
            f"/api/clientes/vendedor/{self.vendedor.pk}/",
            f"/api/vendedores/{self.vendedor.pk}/clientes/",
            "/api/clientes/bairro/Águas%20Claras/",
        )
        for rota in rotas:
            with self.subTest(rota=rota):
                resposta = self.client.get(rota)
                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertEqual(len(resposta.data), 1)
                self.assertEqual(resposta.data[0]["id_cliente"], "CLI-EXEMPLO")
