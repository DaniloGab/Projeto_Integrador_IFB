"""Merged DRF views: Jennie's clients endpoints and Gabriel's vendors API."""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Cliente, Vendedor
from .serializers import ClientesSerializer, VendedorSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by("id")
    serializer_class = ClientesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "razao_social", "cnpj", "telefone", "email", "bairro_informado",
        "cep", "cidade", "uf", "data_cadastro",
    ]
    search_fields = ["razao_social", "cnpj", "bairro_informado", "cidade"]

    @extend_schema(responses=ClientesSerializer(many=True))
    @action(detail=False, methods=["get"], url_path=r"vendedor/(?P<vendedor_id>[0-9]+)")
    def clientes_por_vendedor(self, request, vendedor_id=None):
        clientes = self.filter_queryset(
            self.get_queryset().filter(vendedor_id_id=vendedor_id)
        )
        return Response(self.get_serializer(clientes, many=True).data)

    @extend_schema(responses=ClientesSerializer(many=True))
    @action(detail=False, methods=["get"], url_path=r"bairro/(?P<nome>[^/]+)")
    def clientes_por_bairro(self, request, nome=None):
        clientes = self.filter_queryset(
            self.get_queryset().filter(bairro_informado__iexact=nome)
        )
        return Response(self.get_serializer(clientes, many=True).data)


class VendedorViewSet(viewsets.ModelViewSet):
    queryset = Vendedor.objects.all().order_by("id")
    serializer_class = VendedorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["vendedor_nome"]

    @extend_schema(responses=ClientesSerializer(many=True))
    @action(detail=True, methods=["get"], url_path="clientes")
    def clientes(self, request, pk=None):
        vendedor = self.get_object()
        clientes = Cliente.objects.filter(vendedor_id=vendedor).order_by("id")
        return Response(ClientesSerializer(clientes, many=True).data)
