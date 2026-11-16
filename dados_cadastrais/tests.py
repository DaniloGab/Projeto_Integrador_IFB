
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

