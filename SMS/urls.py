"""SMS URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import include, path, re_path
from . import settings
from django.contrib.staticfiles.urls import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView
urlpatterns = [
    path('', RedirectView.as_view(url='/scolar/index')),
    path('admin/', admin.site.urls),
    path('index', RedirectView.as_view(url='/scolar/index')),
    path('home', RedirectView.as_view(url='/scolar/index')),
    path('home.html', RedirectView.as_view(url='/scolar/index')),
    path('index.html', RedirectView.as_view(url='/scolar/index')),
    path('index.php', RedirectView.as_view(url='/scolar/index')),
    path('index.asp', RedirectView.as_view(url='/scolar/index')),
    path('scolar/', include('scolar.urls')),
   
    path('accounts/', include('django.contrib.auth.urls')),
    re_path(r'^auth/', include('social_django.urls', namespace='social')), # social django endpoints
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)