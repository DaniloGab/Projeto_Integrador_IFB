# Documentação da API REST

## Visão geral

A API gerencia vendedores e clientes da Distribuidora Vetor. Ela foi construída com Django REST Framework e usa SQLite como banco local.

- **Base URL local:** `http://127.0.0.1:8000`
- **Formato:** JSON
- **Documentação interativa:** `/api/docs/`
- **Schema OpenAPI:** `/api/schema/`
- **Arquivo versionado:** [`API_Schema.yaml`](../API_Schema.yaml)

## Autenticação e autorização

A autenticação é feita por token do Django REST Framework.

```http
POST /api/auth/token/
Content-Type: application/json

{
  "username": "USUARIO",
  "password": "SENHA"
}
```

Resposta:

```json
{
  "token": "chave-gerada"
}
```

Envie o token em operações protegidas:

```http
Authorization: Token chave-gerada
```

| Operação | Anônimo | Usuário autenticado |
|---|---:|---:|
| Consultar (`GET`) | Permitida | Permitida |
| Criar (`POST`) | Negada — 401/403 | Permitida |
| Atualizar (`PUT/PATCH`) | Negada — 401/403 | Permitida |
| Excluir (`DELETE`) | Negada — 401/403 | Permitida |

A página `/api/docs/` usa Redoc. O schema é gerado por `drf-spectacular`.

## Recursos

### Vendedor

#### Campos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `id` | inteiro | leitura | Identificador técnico |
| `vendedor_nome` | string | sim | Nome do vendedor |

#### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/vendedores/` | Lista vendedores |
| `POST` | `/api/vendedores/` | Cria vendedor |
| `GET` | `/api/vendedores/{id}/` | Obtém vendedor |
| `PUT` | `/api/vendedores/{id}/` | Atualiza vendedor |
| `PATCH` | `/api/vendedores/{id}/` | Atualiza parcialmente |
| `DELETE` | `/api/vendedores/{id}/` | Remove vendedor sem clientes associados |
| `GET` | `/api/vendedores/{id}/clientes/` | Lista clientes do vendedor |

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/vendedores/ \
  -H "Authorization: Token SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"vendedor_nome":"João Silva"}'
```

### Cliente

#### Campos públicos

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `id` | inteiro | leitura | Identificador técnico Django |
| `id_cliente` | string | não | Identificador externo do CSV |
| `razao_social` | string | sim | Razão social tratada |
| `cnpj` | string | não | CNPJ tratado e mascarado |
| `telefone` | string | não | Telefone tratado |
| `email` | string | não | E-mail tratado |
| `bairro_informado` | string | não | Bairro tratado |
| `cep` | string | não | CEP tratado com hífen |
| `cidade` | string | sim | Cidade |
| `uf` | string | sim | Unidade federativa |
| `data_cadastro` | data ISO | não | Data de cadastro |
| `vendedor_id` | inteiro | sim | Identificador do vendedor responsável |
| `vendedor_responsavel` | string | leitura | Nome do vendedor |
| `possui_pendencia` | booleano | leitura | Indica necessidade de revisão |

Os campos internos — valores originais, bairro consultado, status do CEP, consistência, motivos e confirmação externa — não são publicados pelo serializer público.

#### Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/clientes/` | Lista ou filtra clientes |
| `POST` | `/api/clientes/` | Cria cliente |
| `GET` | `/api/clientes/{id}/` | Obtém cliente |
| `PUT` | `/api/clientes/{id}/` | Atualiza cliente |
| `PATCH` | `/api/clientes/{id}/` | Atualiza parcialmente |
| `DELETE` | `/api/clientes/{id}/` | Remove cliente |
| `GET` | `/api/clientes/vendedor/{vendedor_id}/` | Lista clientes por vendedor |
| `GET` | `/api/clientes/bairro/{nome}/` | Lista clientes por bairro |

#### Filtros e busca

Filtros exatos disponíveis em `GET /api/clientes/`:

- `razao_social`
- `cnpj`
- `telefone`
- `email`
- `bairro_informado`
- `cep`
- `cidade`
- `uf`
- `data_cadastro`

Também existe o parâmetro `search`, que pesquisa em razão social, CNPJ, bairro e cidade.

```text
/api/clientes/?cidade=Brasília
/api/clientes/?search=Águas%20Claras
/api/clientes/vendedor/1/
/api/clientes/bairro/Águas%20Claras/
```

## Validações

### CNPJ

- Remove caracteres não numéricos antes de comparar.
- Exige exatamente 14 dígitos.
- Impede cadastro ou alteração com CNPJ já existente.
- Retorna o valor mascarado no formato `XX.XXX.XXX/XXXX-XX`.

### Cadastramento

- `vendedor_id` deve referenciar um vendedor existente.
- `razao_social`, `cidade` e `uf` são obrigatórios no contrato atual.
- Os dados são retornados com os valores tratados pelo ETL ou informados manualmente.

## Códigos de resposta

| Código | Significado |
|---:|---|
| `200` | Consulta ou alteração realizada |
| `201` | Recurso criado |
| `204` | Recurso removido sem corpo |
| `400` | Dados inválidos |
| `401` | Autenticação ausente ou token inválido |
| `403` | Usuário autenticado sem permissão |
| `404` | Recurso não encontrado |

## Exemplos

### Obter token

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SENHA"}'
```

### Criar cliente

```bash
curl -X POST http://127.0.0.1:8000/api/clientes/ \
  -H "Authorization: Token SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{
    "razao_social":"Mercado Exemplo LTDA",
    "cnpj":"12.345.678/0001-90",
    "telefone":"61999999999",
    "email":"contato@exemplo.com",
    "bairro_informado":"Águas Claras",
    "cep":"72140-010",
    "cidade":"Brasília",
    "uf":"DF",
    "vendedor_id":1
  }'
```

## Modelagem

- [Modelo Entidade‑Relacionamento — MER](MER.md)
- [Diagrama Entidade‑Relacionamento — DER](DER.md)
- [Integração Django e ETL](INTEGRACAO_DJANGO.md)
- [Decisão técnica do ETL](ETL.md)
