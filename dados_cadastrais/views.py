from django.shortcuts import render
from .models import Cliente, Vendedor
from .serializers import ClientesSerializer, VendedorSerializer
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClientesSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['razao_social', 'cnpj', 'telefone', 'email', 'bairro_informado', 'cep', 'cidade', 'uf', 'data_cadastro',]

class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer

# Create your views here.
