from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
<<<<<<< HEAD
from dados_cadastrais.views import ClienteViewSet, VendedorViewSet

router =  DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'vendedores', VendedorViewSet)
=======
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from dados_cadastrais.views import ClienteViewSet, VendedorViewSet

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'veendedores', VendedorViewSet)
>>>>>>> 6ed6c6a (Primeiro Commit)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
<<<<<<< HEAD
=======
    path('api/token/', obtain_auth_token),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
>>>>>>> 6ed6c6a (Primeiro Commit)
]