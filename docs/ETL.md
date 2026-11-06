# ETL Primora — decisão técnica de qualidade de dados

## Objetivo

Limpar e agrupar os 47 clientes fictícios da Distribuidora Vetor sem atribuir informação postal não comprovada. O script `primora_etl.py` gera CSVs para análise, a tabela de auditoria e uma lista de pendências. A gravação no banco configurado pelo Django acontece pelo comando `python manage.py importar_etl --persistir`.

## Política de CEP (decisão recomendada)

| Entrada / consulta | `cep_normalizado` | `status_cep` | `status_consistencia` | Revisão? |
| --- | --- | --- | --- | --- |
| 8 dígitos, sem chamada à API | Preservado com hífen | `NAO_CONSULTADO` | `NAO_VERIFICADA` | Não só por falta de consulta |
| ViaCEP localiza CEP e bairro é equivalente | Preservado com hífen | `LOCALIZADO` | `COMPATIVEL` | Não por CEP |
| ViaCEP localiza CEP, bairro difere | Preservado com hífen | `LOCALIZADO` | `DIVERGENTE_BAIRRO` | Sim |
| ViaCEP localiza CEP, UF difere | Preservado com hífen | `LOCALIZADO` | `DIVERGENTE_UF` | Sim |
| ViaCEP localiza CEP, mas não informa bairro | Preservado com hífen | `LOCALIZADO` | `NAO_AVALIAVEL` | Somente outras pendências |
| ViaCEP retorna `erro: true` | Preservado com hífen | `NAO_LOCALIZADO` | `NAO_AVALIAVEL` | Sim |
| Conexão / erro de servidor | Preservado com hífen | `API_INDISPONIVEL` | `NAO_VERIFICADA` | Sim, reconsultar |
| Ausente | `NULL` | `AUSENTE` | `NAO_AVALIAVEL` | Sim |
| `00000-000` | `NULL` | `AUSENTE_MARCADOR` | `NAO_AVALIAVEL` | Sim |
| Tamanho ou formato inválido | `NULL` | `FORMATO_INVALIDO` | `NAO_AVALIAVEL` | Sim |

**A existência do CEP no ViaCEP não prova que esse é o CEP do cliente.** A existência e a coerência geográfica são informações distintas. Guardamos `bairro_via_cep` como evidência separada, sem sobrescrever `bairro_normalizado` obtido do cadastro e do dicionário de equivalências.

A busca inversa por endereço exige logradouro, ausente no CSV. Portanto o ETL **não busca um CEP a partir de um bairro** e não usa CEP de agência dos Correios como substituto. Também **não preenche Plano Piloto** quando o cadastro apenas informa Brasília/DF.

## Campos principais de saída

- `cep_original`: texto informado, mesmo se `00000-000`.
- `cep_normalizado`: texto `00000-000` apenas quando tem oito dígitos não zerados, ou vazio.
- `status_cep`: estado da verificação de existência/formato.
- `bairro_informado`: bairro original.
- `bairro_normalizado`: agrupamento canônico do cadastro (ou vazio se não identificado).
- `bairro_via_cep`: bairro consultado, usado como **evidência**, não como substituto automático.
- `status_consistencia`: resultado da comparação por grupos canônicos e UF.
- `pendencia_revisao`, `motivos_pendencia`: pendências para intervenção humana.
- `data_cadastro_normalizado`: data exibida como `DD/MM/AAAA` no CSV.
- `data_cadastro_iso`: data em `AAAA-MM-DD` para um `DateField` no Django.

## Outros tratamentos

- Bairros são agrupados por regras determinísticas, por exemplo `Sul (Águas Claras)` → `Águas Claras`. A equipe assume essa equivalência **somente para relatórios**; não significa mesmo CEP ou mesmo logradouro.
- CNPJ fictício: exigir 14 dígitos e aplicar máscara sem validar dígito verificador.
- Telefone: normalização de DDI `55`, DDD e número; não preencher algarismos faltantes.
- E-mail: minúsculas e validação sintática conservadora; o dataset contém e-mails compartilhados. A coluna `email` do Django não deve ser `unique=True`.
- Datas: formatos ISO, brasileiro e nomes de mês em inglês/português, sem interpretações ambíguas fora dos formatos explicitamente aceitos.

## Auditoria e repetibilidade

A auditoria guarda `execucao_id`, `id_cliente`, nome do campo, valor original, tratado, critério, fonte e status. Ela é histórica: repetir o comando preserva os eventos de nova execução, mas os clientes são atualizados por `id_cliente` (`update_or_create`) e não duplicados.

O banco de dados é gerenciado exclusivamente pelas **migrations do Django**. A importação usa `transaction.atomic()` e o ORM, sem criar tabelas com SQL independente. O modelo de auditoria aparece no Django Admin, não em uma rota pública.

### Semântica da auditoria de comparação de bairro

A auditoria de `bairro_informado` registra a transformação textual feita pelo
ETL (por exemplo, `Sul (Aguas Claras)` → `Águas Claras`). A auditoria de
`bairro_via_cep` documenta **consulta/comparação, não conversão de bairro**:
`valor_original` e `valor_tratado` são ambos o nome retornado pelo ViaCEP,
mesmo no caso de `status=CONFLITO`. O `criterio` registra qual bairro normalizado
do cadastro foi comparado e a opção por não sobrescrever nenhum dos dois.

O Django Admin permite **visualizar** a auditoria, mas não criar, editar nem
excluir eventos, inclusive para superusuário. Essa proteção é de interface;
não é uma garantia de imutabilidade contra acesso ao banco, migrações ou
comandos administrativos. A integridade histórica completa requer controles
adicionais de banco e de operação.

**Histórico anterior:** corrigir o código não altera registros já gravados. Uma
nova execução produz novos registros com a semântica correta; preservar o
histórico anterior permite rastrear o que o pipeline registrava à época.

## Limites e trade-offs

- Comparar `bairro_normalizado` com ViaCEP pode gerar falsas divergências quando a nomenclatura do serviço difere da nomenclatura analítica. Por isso há `NAO_AVALIAVEL` e revisão humana.
- O cache guarda respostas conclusivas; indisponibilidades de rede não são tratadas como CEP inexistente.
- A execução offline é reprodutível, mas não verifica a existência dos 31 CEPs de oito dígitos da amostra. Para isso execute com `--consultar-cep`.
- Os 47 clientes e suas datas são fictícios; a avaliação prioriza integridade dos dados e explicitação das decisões, não correção postal inventada.

## Execução

```bash
python -m pip install -r requirements-etl.txt
python -m pytest -q tests/test_primora_etl.py
python primora_etl.py --saida resultados
python primora_etl.py --saida resultados --consultar-cep

# Depois de aplicar as migrações em banco de desenvolvimento:
python manage.py importar_etl --saida resultados --persistir
python manage.py importar_etl --saida resultados --persistir --consultar-cep
```

Para testes de integração com o SQLite em uma base **temporária de testes** do Django:

```bash
python manage.py test dados_cadastrais
```

**Não execute `--persistir` no banco compartilhado sem concordância do Danilo e backup.**
