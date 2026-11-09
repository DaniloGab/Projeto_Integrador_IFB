from django.contrib import admin
from .models import Vendedor, Cliente
from rest_framework.authtoken.models import Token

admin.site.register(Vendedor)
admin.site.register(Cliente)
