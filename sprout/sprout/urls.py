# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from appliances import views

urlpatterns = patterns('',
    # Examples:
    url(r'^$', RedirectView.as_view(pattern_name=views.index, permanent=False), name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^appliances/', include('appliances.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
