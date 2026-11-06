"""Comando: python manage.py importar_etl [--consultar-cep] --persistir

Sem --persistir, gera arquivos CSV sem modificar o banco. Com --persistir,
usa o ORM, os modelos e a conexão DATABASES do Django (SQLite ou PostgreSQL).
"""
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from dados_cadastrais.models import AuditoriaETL, Cliente, Vendedor
from primora_etl import ClienteViaCEP, extrair_csv, salvar_csv_e_relatorio, transformar


class Command(BaseCommand):
    help = "Limpa o CSV da Primora e importa clientes, vendedores e auditoria para o banco Django."

    def add_arguments(self, parser):
        raiz = Path(__file__).resolve().parents[3]
        parser.add_argument("--csv", type=Path, default=raiz / "02-clientes_distribuidora_vetor.csv")
        parser.add_argument("--saida", type=Path, default=raiz / "resultados")
        parser.add_argument("--consultar-cep", action="store_true", help="Ativa consultas reais ao ViaCEP")
        parser.add_argument("--cache", type=Path, help="Caminho do cache ViaCEP")
        parser.add_argument("--persistir", action="store_true", help="Salva no SQLite/PostgreSQL do Django")

    def handle(self, *args, **opts):
        # A leitura e transformação são as mesmas usadas fora do Django.
        origem = extrair_csv(opts["csv"])
        cliente_api = (ClienteViaCEP(opts["cache"] or opts["saida"] / "cache_viacep.json")
                       if opts["consultar_cep"] else None)
        clientes, vendedores, auditoria, pendencias, resumo = transformar(
            origem, consulta_cep=cliente_api.consultar if cliente_api else None
        )
        salvar_csv_e_relatorio(clientes, vendedores, auditoria, pendencias, resumo, opts["saida"])
        if cliente_api:
            cliente_api.salvar_cache()
        self.stdout.write(
            f"ETL: {len(clientes)} clientes, {len(vendedores)} vendedores; "
            f"{len(auditoria)} eventos de auditoria e {len(pendencias)} clientes com pendência."
        )
        if not opts["persistir"]:
            self.stdout.write("Modo de conferência: o banco NÃO foi alterado. Acrescente --persistir para importar.")
            return

        if clientes["vendedor_id"].isna().any():
            raise CommandError("A importação foi bloqueada: cliente sem vendedor responsável.")

        # Mesma ideia do importarDados.py dos filmes: criar/reutilizar vendedor e
        # associar seus clientes. A transação evita uma importação parcial.
        criados = atualizados = 0
        with transaction.atomic():
            mapa_vendedores = {}
            for _, linha_vendedor in vendedores.iterrows():
                nome = linha_vendedor["nome_vendedor"]
                try:
                    vendedor, _ = Vendedor.objects.get_or_create(vendedor_nome=nome)
                except Vendedor.MultipleObjectsReturned as exc:
                    raise CommandError(
                        f"Há mais de um vendedor com o nome {nome!r}; resolva duplicidades antes de importar."
                    ) from exc
                mapa_vendedores[int(linha_vendedor["id_vendedor"])] = vendedor

            # Mapeia ID do CSV ao registro; rerun atualiza, não duplica.
            por_id = {linha["id_cliente"]: linha for _, linha in origem.iterrows()}
            for _, linha in clientes.iterrows():
                bruto = por_id[linha["id_cliente"]]
                data_iso = linha["data_cadastro_iso"]
                _, criado = Cliente.objects.update_or_create(
                    id_cliente=linha["id_cliente"],
                    defaults={
                        "razao_social": linha["razao_social"],
                        "cnpj": bruto["cnpj"],
                        "cnpj_normalizado": linha["cnpj_normalizado"],
                        "telefone": bruto["telefone"],
                        "telefone_normalizado": linha["telefone_normalizado"],
                        "email": linha["email"],
                        "bairro_informado": bruto["bairro_informado"],
                        "bairro_normalizado": linha["bairro_normalizado"],
                        "cep": bruto["cep"],
                        "cep_normalizado": linha["cep_normalizado"],
                        "status_cep": linha["status_cep"],
                        "status_consistencia": linha["status_consistencia"],
                        "bairro_via_cep": linha["bairro_via_cep"],
                        "cep_confirmado_via_cep": bool(linha["cep_confirmado_via_cep"]),
                        "necessita_revisao": bool(linha["pendencia_revisao"]),
                        "motivos_pendencia": linha["motivos_pendencia"],
                        "cidade": linha["cidade"],
                        "uf": linha["uf"],
                        "data_cadastro": bruto["data_cadastro"],
                        "data_cadastro_normalizado": date.fromisoformat(data_iso) if data_iso else None,
                        "vendedor_id": mapa_vendedores[int(linha["vendedor_id"])],
                    },
                )
                if criado:
                    criados += 1
                else:
                    atualizados += 1

            # A auditoria é histórica. Reexecutar gera uma execução adicional,
            # mas clientes não duplicam, pois há update_or_create por id_cliente.
            AuditoriaETL.objects.bulk_create([
                AuditoriaETL(
                    execucao_id=linha["execucao_id"],
                    id_cliente=linha["id_cliente"],
                    campo=linha["campo"],
                    valor_original=linha["valor_original"],
                    valor_tratado=linha["valor_tratado"],
                    criterio=linha["criterio"],
                    fonte=linha["fonte"],
                    status=linha["status"],
                ) for _, linha in auditoria.iterrows()
            ])
        self.stdout.write(self.style.SUCCESS(
            f"Carga concluída! {criados} clientes criados, {atualizados} atualizados; "
            f"{Vendedor.objects.count()} vendedores e {Cliente.objects.count()} clientes no banco."
        ))
