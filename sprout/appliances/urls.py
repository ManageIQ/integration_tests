from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import login, logout, password_change

from appliances import api, views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'api$', csrf_exempt(api.jsonapi)),
    url(r'api.html$', api.jsonapi_doc),
    url(r'providers.html$', views.providers),
    url(r'templates.html$', views.templates),
    url(r'my-appliances.html$', views.my_appliances),
    url(r'shepherd.html$', views.shepherd),
    url(r'^login$', login, {'template_name': 'login.html'}),
    url(r'^change_password$', password_change, {'template_name': 'password.html'}),
    url(r'^change_password.done$', views.go_home, name='password_change_done'),
    url(r'^logout$', logout),
    url(r'appliance.start/(?P<appliance_id>\d+)$', views.start_appliance),
    url(r'appliance.stop/(?P<appliance_id>\d+)$', views.stop_appliance),
    url(r'appliance.suspend/(?P<appliance_id>\d+)$', views.suspend_appliance),
    url(r'appliance.prolong/(?P<appliance_id>\d+)/(?P<minutes>\d+)$',
        views.prolong_lease_appliance),
    url(r'appliance.dontexpiry/(?P<appliance_id>\d+)$', views.dont_expire_appliance),
    url(r'appliance.kill/(?P<appliance_id>\d+)$', views.kill_appliance),
    url(r'template.delete-provider/(?P<template_id>\d+)$', views.delete_template_provider),
    url(r'versions.group$', views.versions_for_group),
    url(r'date.version_group$', views.date_for_group_and_version),
    url(r'providers_for_request$', views.providers_for_date_group_and_version),
    url(r'pool.request$', views.request_pool),
    url(r'pool.transfer$', views.transfer_pool),
    url(r'pool.kill/(?P<pool_id>\d+)$', views.kill_pool),
    url(r'vms$', views.vms, name="vms_default"),
    url(r'vms.at/(?P<current_provider>[a-z_A-Z0-9-]+)$', views.vms, name="vms_at_provider"),
    url(r'vms.at/(?P<current_provider>[a-z_A-Z0-9-]+)/list$', views.vms_table),
    url(r'vm.power/([a-z_A-Z0-9-]+)$', views.power_state),
    url(r'vm.buttons/([a-z_A-Z0-9-]+)$', views.power_state_buttons),
    url(r'vm.action/([a-z_A-Z0-9-]+)$', views.vm_action),
)
