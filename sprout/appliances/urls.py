from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import login, logout, password_change

from appliances import api, views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^api$', csrf_exempt(api.jsonapi)),
    url(r'^api.html$', api.jsonapi_doc),
    url(r'^providers$', views.providers),
    url(r'^templates$', views.templates),
    url(r'^templates/delete/(?P<template_id>\d+)$', views.delete_template_provider),
    url(r'^appliances$', views.my_appliances),
    url(r'^appliances/start/(?P<appliance_id>\d+)$', views.start_appliance),
    url(r'^appliances/stop/(?P<appliance_id>\d+)$', views.stop_appliance),
    url(r'^appliances/suspend/(?P<appliance_id>\d+)$', views.suspend_appliance),
    url(r'^appliances/prolong/(?P<appliance_id>\d+)/(?P<minutes>\d+)$',
        views.prolong_lease_appliance),
    url(r'^appliances/dontexpire/(?P<appliance_id>\d+)$', views.dont_expire_appliance),
    url(r'^appliances/kill/(?P<appliance_id>\d+)$', views.kill_appliance),
    url(r'^shepherd$', views.shepherd),
    url(r'^login$', login, {'template_name': 'login.html'}),
    url(r'^change_password$', password_change, {'template_name': 'password.html'}),
    url(r'^change_password/done$', views.go_home, name='password_change_done'),
    url(r'^logout$', logout),
    url(r'^pool/request$', views.request_pool),
    url(r'^pool/transfer$', views.transfer_pool),
    url(r'^pool/kill/(?P<pool_id>\d+)$', views.kill_pool),
    url(r'^vms$', views.vms, name="vms_default"),
    url(r'^vms/(?P<current_provider>[a-z_A-Z0-9-]+)$', views.vms, name="vms_at_provider"),
    url(r'^ajax/vms/(?P<current_provider>[a-z_A-Z0-9-]+)$', views.vms_table, name="vms_table"),
    url(r'^ajax/versions_for_group$', views.versions_for_group),
    url(r'^ajax/date_for_version_group$', views.date_for_group_and_version),
    url(r'^ajax/providers_for_date_group_version$', views.providers_for_date_group_and_version),
    url(r'^ajax/vms/power/([a-z_A-Z0-9-]+)$', views.power_state),
    url(r'^ajax/vms/buttons/([a-z_A-Z0-9-]+)$', views.power_state_buttons),
    url(r'^ajax/vms/action/([a-z_A-Z0-9-]+)$', views.vm_action),
)
