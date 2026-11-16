

from django.shortcuts import render
from .models import Cliente, Vendedor
from .serializers import ClientesSerializer, VendedorSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClientesSerializer
    filter_backends = [DjangoFilterBackend]

    filterset_fields = [
        'razao_social',
        'cnpj',
        'telefone',
        'email',
        'bairro_informado',
        'cep',
        'cidade',
        'uf',
        'data_cadastro',
    ]

    @action(
        detail=False,
        methods=['get'],
        url_path=r'vendedor/(?P<vendedor_id>[0-9]+)'
    )
    def clientes_por_vendedor(self, request, vendedor_id=None):
        clientes = self.get_queryset().filter(
            vendedor_id_id=vendedor_id
        )

        serializer = self.get_serializer(clientes, many=True)

        return Response(serializer.data)


class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer
