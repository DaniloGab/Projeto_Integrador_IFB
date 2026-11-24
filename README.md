# API de Vendedores, Autenticação e Permissões

**Responsável:** Gabriel (Integrante 4)
**Branch:** `api-vendedores-gabriel`
**Commit principal:** `1d04875` — "API - Vendedores" (09/11/2026)
**Projeto:** Projeto Integrador Primora — Distribuidora Vetor (Parte 2: API REST em Django)

---

## 1. Objetivo da minha parte

Pelo plano de ação da equipe, minha responsabilidade foi a camada de **vendedores e segurança** da API:

- CRUD de vendedores (`/api/vendedores/`);
- consulta dos clientes de um vendedor (`/api/vendedores/{id}/clientes/`);
- autenticação por **Django Auth + Token Authentication (DRF)** (`/api/auth/token/`);
- controle de acesso: usuário logado faz CRUD completo, usuário não logado só consulta (GET);
- schema **OpenAPI** com `drf-spectacular`, exibido em **Redoc** (`/api/docs/`);
- registro das tabelas no **admin**.

---

## 2. O que foi feito

### 2.1 Arquivos modificados

| Arquivo                     | O que mudou                                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `core/settings.py`          | Adicionei `rest_framework.authtoken` e `drf_spectacular` ao `INSTALLED_APPS`. Troquei a permissão global de `AllowAny` para `IsAuthenticatedOrReadOnly`, habilitei `TokenAuthentication` e defini `DEFAULT_SCHEMA_CLASS` do drf-spectacular. Mantive o `DjangoFilterBackend` já existente. Criei o bloco `SPECTACULAR_SETTINGS` (título, descrição, versão e `REDOC_DIST`). |
| `core/urls.py`              | Adicionei as rotas `api/auth/token/` (token), `api/schema/` (schema OpenAPI) e `api/docs/` (Redoc).                                                                                                                                                                                                                                                                         |
| `dados_cadastrais/views.py` | Limpei os imports, adicionei filtro por nome na `VendedorViewSet` e criei a action `clientes`, que gera `/api/vendedores/{id}/clientes/`, documentada com `@extend_schema`.                                                                                                                                                                                                 |
| `dados_cadastrais/admin.py` | Registrei `Vendedor` e `Cliente` no admin do Django.                                                                                                                                                                                                                                                                                                                        |

### 2.2 Detalhes das decisões

**Permissões globais.** A configuração original estava com `AllowAny`, ou seja, qualquer pessoa sem login conseguiria fazer POST/PUT/DELETE, o que contraria o requisito do enunciado. Passei para `IsAuthenticatedOrReadOnly` no `settings.py`. Como a regra é global, ela vale também para a API de clientes, sem precisar repetir em cada viewset.

**Token.** Usei a view pronta `obtain_auth_token` do DRF. O cliente envia `username` e `password` por POST e recebe um token, que depois é enviado no cabeçalho `Authorization: Token <token>`. A tabela de tokens é criada pela migração do app `rest_framework.authtoken`.

**Rota de clientes do vendedor.** Implementada como `@action(detail=True)` na `VendedorViewSet`. Se o vendedor não existe, o `get_object()` retorna 404 automaticamente.

**Redoc fixado em versão estável.** Ao abrir `/api/docs/` a página ficava em branco. O console do navegador mostrava `Uncaught SyntaxError: import.meta may only appear in a module` no arquivo `redoc.standalone.js`. A causa era a URL com `redoc@latest` usada por padrão. A solução foi fixar a versão com `REDOC_DIST = 'https://cdn.jsdelivr.net/npm/redoc@2.1.5'` no `SPECTACULAR_SETTINGS`. Depois disso a documentação passou a carregar normalmente.

**Admin.** `Vendedor` e `Cliente` foram registrados com `admin.site.register`. O model `Token` não precisa ser registrado manualmente, porque o `rest_framework.authtoken` já faz isso sozinho.

---

## 3. Como testei

Os testes foram **manuais**, com o servidor local (`python manage.py runserver`) e `curl` em outro terminal.

**Preparação**

```bash
python manage.py migrate            # cria a tabela de tokens (authtoken)
python manage.py createsuperuser    # usuário para pedir o token
python manage.py runserver
```

**Casos testados**

| #   | Teste                    | Comando (resumo)                                       | Esperado                                       | Resultado                                                                                                                           |
| --- | ------------------------ | ------------------------------------------------------ | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Leitura sem login        | `curl -i http://127.0.0.1:8000/api/vendedores/`        | 200                                            | OK                                                                                                                                  |
| 2   | Escrita sem login        | `POST /api/vendedores/` sem cabeçalho                  | 401                                            | OK                                                                                                                                  |
| 3   | Pedir token              | `POST /api/auth/token/` com usuário e senha            | 200 + `{"token": "..."}`                       | OK (após corrigir a rota, veja abaixo)                                                                                              |
| 4   | Escrita com token válido | `POST /api/vendedores/` com `Authorization: Token ...` | 201                                            | OK                                                                                                                                  |
| 5   | Token inválido           | `POST` com `Authorization: Token tokenfalso`           | 401 `Invalid token.`                           | OK                                                                                                                                  |
| 6   | Clientes de um vendedor  | `GET /api/vendedores/1/clientes/`                      | 200 com lista, ou 404 se o vendedor não existe | 404 `No Vendedor matches the given query` com o banco vazio, o que é o esperado; a rota aparece registrada como `vendedor-clientes` |
| 7   | Documentação             | abrir `/api/docs/` no navegador                        | Página Redoc                                   | OK após fixar o Redoc em 2.1.5                                                                                                      |

Exemplo de uso:

```bash
# pegar o token
curl -X POST http://127.0.0.1:8000/api/auth/token/ -d "username=admin&password=SUA_SENHA"

# criar vendedor com token
curl -i -X POST http://127.0.0.1:8000/api/vendedores/ \
  -H "Authorization: Token SEU_TOKEN" \
  -d "vendedor_nome=Teste"
```

**Problemas encontrados durante os testes**

1. **404 em `/api/auth/token/`:** o `urls.py` ainda tinha o caminho antigo `api/token/`. Corrigi para `api/auth/token/`, como pede o enunciado.
2. **Redoc em branco:** explicado na seção 2.2 (fixação da versão do Redoc).
3. **Senha rejeitada no `createsuperuser`:** o Django valida a senha por padrão (mínimo de 8 caracteres, não muito comum, não só números). Mantive as validações ativas e usei uma senha que passa nas regras.

---

## 4. Pendências conhecidas

| Item                                    | Observação                                                                                                                                                                                                             |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `drf-spectacular` no `requirements.txt` | O arquivo ainda não lista `drf-spectacular`. É necessário adicionar (junto com `django-filter` e `djangorestframework`, que já estão) para o projeto instalar do zero.                                                 |
| Rota `/api/clientes/vendedor/{id}/`     | Ainda não implementada. Está nas rotas obrigatórias. Como a `ClienteViewSet` é da Integrante 3, combinar quem adiciona a action para evitar conflito.                                                                  |
| Nomes dos models                        | O `models.py` atual usa `vendedor_nome` e `vendedor_id` (FK). O plano prevê `nome_vendedor` e FK `vendedor`. Quando o Danilo fechar os models, ajustar `filterset_fields` e o `filter(vendedor_id=...)` em `views.py`. |
| Auditoria no admin                      | Registrar o model `Auditoria` no `admin.py` quando ele existir.                                                                                                                                                        |
| `import` não usado em `admin.py`        | O `from rest_framework.authtoken.models import Token` não é utilizado e pode ser removido.                                                                                                                             |
| Testes automatizados                    | Os testes acima foram manuais. Eles servem de base para os testes automatizados (GET público 200, escrita anônima 401, escrita com token 201, token falso 401).                                                        |

---

## 5. Resumo

- Segurança por token funcionando: anônimo só lê, logado altera.
- CRUD de vendedores e a rota `/api/vendedores/{id}/clientes/` funcionando.
- Documentação OpenAPI/Redoc em `/api/docs/` funcionando, com Redoc fixado na versão 2.1.5.
- Admin com `Vendedor` e `Cliente` registrados.
- Falta fechar a rota `clientes/vendedor/{id}/`, atualizar o `requirements.txt` e ajustar os nomes dos campos quando os models forem definidos.

# 📘 Projeto Integrador API e ETL - Desafio Primora

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.0%2B-green.svg?logo=Django)](https://www.djangoproject.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

---

## Orientador:

Diego M. Oliveira
https://github.com/diegomoliveiraprof

---
