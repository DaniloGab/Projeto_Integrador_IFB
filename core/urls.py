from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dados_cadastrais.views import ClienteViewSet, VendedorViewSet

router =  DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'vendedores', VendedorViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]