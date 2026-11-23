# Integração do ETL com Django — proposta aprovada de nomenclatura (23/11/2026)

Este conjunto de arquivos foi preparado **a partir do ZIP `feature/etl` recebido em 23/11**. Ele não contém a API de Jennie nem a API de Gabriel. **Não fazer merge antes de revisar a migração e testar em banco descartável.**

## Contrato dos dados

- `Cliente.cnpj`, `telefone`, `email`, `cep`, `bairro_informado` e `data_cadastro`: **valores tratados** que serão apresentados na API.
- `Cliente.cnpj_original`, `telefone_original`, `email_original`, `cep_original`, `bairro_informado_original`, `data_cadastro_original`: texto **exatamente recebido** do CSV; somente internos.
- `Cliente.necessita_revisao`: sinalizador interno usado na API com o nome **`possui_pendencia`**, via serializer do responsável pela API de clientes.
- `Cliente.status_cep`, `status_consistencia`, `bairro_via_cep` e `motivos_pendencia`: diagnósticos internos; não incluir na API pública.
- `AuditoriaETL`: histórico detalhado, consultável no Django Admin (sem edição pelo Admin).
- O ETL `primora_etl.py` mantém as saídas `*_normalizado`; a conversão de nomes ocorre em `importar_etl.py`.
- `id_cliente` (do CSV) permanece distinto da chave primária numérica interna do Django.

## Mudanças aplicadas somente à branch do ETL

- `models.py`: campos tratados/originais e modelo `AuditoriaETL`.
- `migrations/0002_integracao_etl.py`: proposta **dependente de `0001_initial` da base de 23/11**.
- `management/commands/importar_etl.py`: mapeamento de valores e preservação dos originais.
- `admin.py`: exibe auditoria sem criação/edição/exclusão pela interface.
- `tests.py`: testes da persistência no banco de testes isolado do Django.

## Ações que cabem aos colegas

- **Jennie:** serializer da API com lista explícita de campos; nunca usar `fields = '__all__'` após criar os campos internos. Expor `possui_pendencia = BooleanField(source='necessita_revisao', read_only=True)`; validar filtros por bairro.
- **Gabriel:** integrar autenticação/permissões e declarar `drf-spectacular` em `requirements.txt` se importar suas rotas de documentação.
- **Samuel:** atualizar testes integrados, README, MER/DER e documentação.
- **Danilo:** revisar se a `0002` já existe na base; se existir, **não copiar/substituir a proposta**. Coordenar merge das branches e validação final.

## Passos de teste em uma cópia local limpa

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-etl.txt
python -m pytest -q tests/test_primora_etl.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test dados_cadastrais
python manage.py showmigrations dados_cadastrais
python manage.py migrate                    # SOMENTE banco local descartável
python manage.py importar_etl --saida resultados_conferencia
python manage.py importar_etl --saida resultados_conferencia --persistir
python manage.py shell -c "from dados_cadastrais.models import Cliente,Vendedor,AuditoriaETL; print(Cliente.objects.count(),Vendedor.objects.count(),AuditoriaETL.objects.count())"
```

Primeira carga offline em SQLite vazio: 47 clientes, 5 vendedores, 217 eventos de auditoria. Cada reexecução preserva clientes por `id_cliente` e acrescenta eventos históricos.

## Precauções

- A migração converte `data_cadastro` de `DateTimeField(auto_now_add=True)` para `DateField`. Em banco preexistente, rever dados e fazer **backup antes de migrar**; os campos `_original` só são preenchidos corretamente ao reimportar o CSV.
- Um CEP `LOCALIZADO` significa que foi encontrado no ViaCEP, **não comprova o endereço do cliente**.
- Uma pendência falsa significa apenas que não foi detectada pela validação executada, não garantia de validade absoluta.
- Não publicar `SECRET_KEY` de produção nem usar `DEBUG=True` em produção.
- O modo com CEP em tempo real requer rede; o modo offline basta para os testes reproduzíveis.
