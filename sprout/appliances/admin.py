# -*- coding: utf-8 -*-
from django.contrib import admin

# Register your models here.
from appliances.models import Provider, Template, Appliance, Group, AppliancePool

admin.site.register(Provider)
admin.site.register(Template)
admin.site.register(Appliance)
admin.site.register(Group)
admin.site.register(AppliancePool)
