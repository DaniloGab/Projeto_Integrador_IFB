
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Cliente, Vendedor


class ClienteAPITestCase(APITestCase):

    def setUp(self):
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
