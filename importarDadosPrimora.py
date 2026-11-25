"""Atalho opcional, inspirado no importarDados.py do projeto de filmes.

Equivale a: python manage.py importar_etl --persistir
(Adicione --consultar-cep se quiser consultar a API.)
"""
import os
import sys
from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
if __name__ == "__main__":
    execute_from_command_line([sys.argv[0], "importar_etl", "--persistir", *sys.argv[1:]])
