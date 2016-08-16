# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from appliances import views

urlpatterns = [
    # Examples:
    url(r'^$', RedirectView.as_view(pattern_name=views.index, permanent=False), name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^appliances/', include('appliances.urls')),
    url(r'^admin/', include(admin.site.urls)),
]
