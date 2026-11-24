"""Public DRF contract. Provenance and audit metadata remain internal."""
import re

from rest_framework import serializers

from .models import Cliente, Vendedor


class VendedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendedor
        fields = ("id", "vendedor_nome")


class ClientesSerializer(serializers.ModelSerializer):
    possui_pendencia = serializers.BooleanField(source="necessita_revisao", read_only=True)
    vendedor_responsavel = serializers.CharField(source="vendedor_id.vendedor_nome", read_only=True)

    class Meta:
        model = Cliente
        fields = (
            "id", "id_cliente", "razao_social", "cnpj", "telefone", "email",
            "bairro_informado", "cep", "cidade", "uf", "data_cadastro",
            "vendedor_id", "vendedor_responsavel", "possui_pendencia",
        )
        read_only_fields = ("id",)

    def validate_cnpj(self, valor):
        """Retain the duplicate-CNPJ rule from the original clients API.

        The model stores treated CNPJ values, which may have different masks
        in imported/manual records. Compare digits rather than punctuation.
        """
        if not valor:
            return valor
        digitos = re.sub(r"[^0-9]", "", valor)
        if len(digitos) != 14:
            raise serializers.ValidationError("O CNPJ precisa ter 14 dígitos.")
        existentes = Cliente.objects.all()
        if self.instance is not None:
            existentes = existentes.exclude(pk=self.instance.pk)
        for cnpj_existente in existentes.values_list("cnpj", flat=True):
            if cnpj_existente and re.sub(r"[^0-9]", "", cnpj_existente) == digitos:
                raise serializers.ValidationError("Já existe um cliente com este CNPJ.")
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
