"""Admin de cadastro e histórico ETL somente para leitura."""
from django.contrib import admin
from .models import AuditoriaETL, Cliente, Vendedor


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ("id", "vendedor_nome")
    search_fields = ("vendedor_nome",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id_cliente", "razao_social", "bairro_informado", "cep", "necessita_revisao")
    search_fields = ("id_cliente", "razao_social", "cnpj", "cep")
    list_filter = ("status_cep", "status_consistencia", "necessita_revisao", "bairro_informado")


@admin.register(AuditoriaETL)
class AuditoriaETLAdmin(admin.ModelAdmin):
    list_display = ("id_cliente", "campo", "status", "fonte", "execucao_id", "criado_em")
    list_filter = ("status", "campo")
    search_fields = ("id_cliente", "execucao_id", "campo")
    readonly_fields = ("execucao_id", "id_cliente", "campo", "valor_original", "valor_tratado",
                       "criterio", "fonte", "status", "criado_em")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
