from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Cliente, Vendedor
from .serializers import ClientesSerializer, VendedorSerializer



class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClientesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'razao_social', 'cnpj', 'telefone', 'email', 'bairro_informado',
        'cep', 'cidade', 'uf', 'data_cadastro',
    ]



class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vendedor_nome']   # nome atual do campo no model

    # GET /api/vendedores/{id}/clientes/
    @extend_schema(responses=ClientesSerializer(many=True))
    @action(detail=True, methods=['get'], url_path='clientes')
    def clientes(self, request, pk=None):
        vendedor = self.get_object()
        clientes = Cliente.objects.filter(vendedor_id=vendedor)
        serializer = ClientesSerializer(clientes, many=True)
        return Response(serializer.data)