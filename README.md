# 📘 Projeto Integrador API e ETL - Desafio Primora

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.0%2B-green.svg?logo=Django)](https://www.djangoproject.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

---

## Visão geral

Este projeto combina uma API REST em Django com um processo de ETL para tratar, padronizar e disponibilizar dados cadastrais de clientes de uma distribuidora. A solução permite armazenar informações em banco de dados, consultar por filtros e limpar dados brutos provenientes de arquivos CSV.

A aplicação foi desenvolvida como parte do Projeto Integrador do IFB e integra conceitos de backend, APIs REST, autenticação, documentação de API e processamento de dados.

---

## Funcionalidades

- API REST para gerenciamento de clientes
- API REST para gerenciamento de vendedores
- autenticação por token via DRF
- documentação automática da API com drf-spectacular
- filtros por campos do modelo
- ETL para normalização de dados de clientes
- limpeza e validação de:
  - CNPJ
  - telefone
  - e-mail
  - data de cadastro
  - CEP e bairro
- integração com a API ViaCEP para padronização de bairros

---

## Tecnologias utilizadas

- Python
- Django
- Django REST Framework
- SQLite
- Pandas
- Requests
- drf-spectacular
- Django Filters

---

## Estrutura do projeto

```text
Projeto_Integrador_IFB-Documents/
├── core/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── dados_cadastrais/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── views.py
│   └── migrations/
├── manage.py
├── primora_etl.py
├── requirements.txt
├── 02-clientes_distribuidora_vetor.csv
└── README.md
```

---

## Modelos principais

### Cliente

Campos principais:

- razao_social
- cnpj
- telefone
- email
- bairro_informado
- cep
- cidade
- uf
- data_cadastro
- vendedor_id

### Vendedor

Campos principais:

- vendedor_nome

---

## Rotas principais da API

- `/api/clientes/`
- `/api/veendedores/`
- `/api/token/`
- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

---

## ETL realizado

O arquivo [primora_etl.py](primora_etl.py) realiza diversas transformações nos dados importados do CSV:

- remoção de caracteres inválidos do CNPJ
- padronização do telefone em formato brasileiro
- limpeza e validação de e-mails
- normalização de datas
- tratamento do CEP
- consulta de bairro via API do ViaCEP
- armazenamento das informações tratadas em um DataFrame do pandas

---

## Como executar o projeto

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd Projeto_Integrador_IFB-Documents
```

### 2. Criar ambiente virtual

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Rodar migrações

```bash
python manage.py migrate
```

### 5. Iniciar o servidor

```bash
python manage.py runserver
```

---

## Acesso à documentação

Após iniciar o servidor, a documentação da API pode ser acessada em:

- http://localhost:8000/api/docs/
- http://localhost:8000/api/redoc/
- http://localhost:8000/api/schema/

---

## Observações

- O projeto usa SQLite para facilitar execução local.
- O arquivo ETL é executado como script separado e não como parte do fluxo web da API.
- A autenticação por token está habilitada para uso dos endpoints da API.

---

## Orientador

Diego M. Oliveira  
https://github.com/diegomoliveiraprof

---
