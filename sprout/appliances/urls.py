from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from appliances import api

urlpatterns = patterns('',
    # url(r'^$', views.index, name='index'),
    url(r'api$', csrf_exempt(api.jsonapi)),
    url(r'api.html$', api.jsonapi.doc),
)
