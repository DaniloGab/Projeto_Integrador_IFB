
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
