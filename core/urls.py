from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dados_cadastrais.views import ClienteViewSet, VendedorViewSet
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

router =  DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'vendedores', VendedorViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
   path('api/auth/token/', obtain_auth_token, name='api-token'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularRedocView.as_view(url_name='schema'), name='docs'),

]