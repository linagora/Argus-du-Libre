"""
URL configuration for argus_du_libre project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from argus_du_libre.admin import admin_site
from public.sitemaps import sitemaps as public_sitemaps

urlpatterns = [
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": public_sitemaps}, name="sitemap"),
]

urlpatterns += i18n_patterns(
    path("admin/", admin_site.urls),
    path("", include("public.urls")),
)
