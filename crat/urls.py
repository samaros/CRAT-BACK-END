from django.contrib import admin
from django.urls import path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from crat.views import stage_view, tokens_view, whitelist_view, is_whitelisted_view, signature_view, stages_view

schema_view = get_schema_view(
    openapi.Info(
        title='CRAT Backend API',
        default_version='v1',
        description='CRAT Backend API',
        license=openapi.License(name='MIT License'),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('api/v1/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('admin/', admin.site.urls),
    path('api/v1/stage/', stage_view),
    path('api/v1/stages/', stages_view),
    path('api/v1/tokens/', tokens_view),
    path('api/v1/whitelist/', whitelist_view),
    path('api/v1/is_whitelisted/<str:address>/', is_whitelisted_view),
    path('api/v1/signature/', signature_view),
]
