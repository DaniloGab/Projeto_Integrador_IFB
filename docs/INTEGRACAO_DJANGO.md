# Integração Primora + Django (proposta sobre o ZIP de 05/11/2026)

## Como difere da importação dos filmes

O `importarDados.py` do exercício dos filmes usa `csv.DictReader` e `sqlite3` com `SELECT/INSERT` para descobrir ou criar um gênero e associar cada filme a ele. O comando de gerenciamento do Primora usa a **mesma ideia**, mas `Vendedor.objects.get_or_create()` e `Cliente.objects.update_or_create()` (ORM Django). Assim, respeita modelos/migrações, funciona com SQLite e PostgreSQL e permite repetir a importação sem duplicar clientes.

## ATENÇÃO — trabalho simultâneo de outras pessoas

Os arquivos `models.py`, `admin.py`, `views.py` e a migration `0002_etl_normalizado.py` no **projeto completo demonstrativo** são uma proposta de integração baseada no ZIP do grupo enviado em 05/11. Eles **não foram aplicados ao repositório GitHub**. Se os colegas alteraram os modelos depois disso, revisar/mesclar essas alterações em conjunto antes de copiar.

A pasta de atualização ETL (pacote pequeno) contém apenas o `primora_etl.py`, testes, comando e documentação. Os arquivos que alteram o schema ficam separados no projeto completo e na pasta `proposta_integracao_django/` do pacote pequeno para aprovação.

### Mudanças necessárias na modelagem

- `Cliente.id_cliente`: identificador do CSV, único e preservado para evitar importações duplicadas (além da PK numérica do Django).
- Campos originais `cnpj`, `telefone`, `cep`, `bairro_informado`, `data_cadastro`: mantidos para compatibilidade com rotas existentes; `data_cadastro` fica como texto original, não `auto_now_add`.
- Campos tratados: `cnpj_normalizado`, `telefone_normalizado`, `bairro_normalizado`, `cep_normalizado` (`max_length=9`), `data_cadastro_normalizado` (`DateField`).
- Diagnóstico postal: `bairro_via_cep`, `status_cep`, `status_consistencia`, `cep_confirmado_via_cep`, `necessita_revisao`, `motivos_pendencia`.
- `email`: sem unicidade; quatro clientes compartilham o mesmo e-mail fictício.
- `AuditoriaETL`: tabela de histórico visível no admin; sem endpoint público.
- `Vendedor`: é resolvido pelo nome durante a carga; o campo de FK original `vendedor_id` é mantido, embora seu nome seja pouco habitual no Django.

### Como executar com SQLite de desenvolvimento

Na raiz do projeto, usando o ambiente virtual:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-etl.txt
python manage.py check
python manage.py showmigrations dados_cadastrais
python manage.py migrate
python manage.py importar_etl --saida resultados
python manage.py importar_etl --saida resultados --persistir
python manage.py test dados_cadastrais
```

Opcionalmente, o pequeno `importarDadosPrimora.py` executa a carga com o mesmo resultado:

```bash
python importarDadosPrimora.py --saida resultados
```

No projeto do ZIP, `core/settings.py` já aponta para `db.sqlite3`. **Não é preciso criar esse arquivo manualmente**, pois `migrate` o cria. O `.gitignore` já exclui `db.sqlite3` do GitHub.

Verificação rápida no console Django:

```bash
python manage.py shell -c "from dados_cadastrais.models import Cliente,Vendedor,AuditoriaETL; print(Cliente.objects.count(), Vendedor.objects.count(), AuditoriaETL.objects.count())"
```

Os dois primeiros números devem ser 47 e 5 após a primeira carga completa. O total de auditoria cresce a cada execução.

### Migração e backup

A migration `0002_etl_normalizado.py` foi escrita para a `0001_initial.py` do ZIP recebido. **Não substitua a migration de outra pessoa** se o histórico do GitHub já tiver mudado. Se já existir `db.sqlite3` com dados relevantes, faça backup, execute `showmigrations`, revise as alterações com Danilo e teste primeiro em uma cópia. A troca de `data_cadastro` para texto preserva a informação original como texto, mas deve ser revista caso já haja registros reais no banco.

### Ações não cobertas pelo ETL

Autenticação Token do DRF, permissões GET público/escrita autenticada, rotas específicas por vendedor/bairro, schema OpenAPI, Redoc e configuração futura do PostgreSQL são tarefas da equipe da API e não são concluídas por esse pacote. A `views.py` demonstrativa mantém o CRUD básico e adiciona filtros de dados normalizados; o sistema completo ainda depende dessas frentes.
