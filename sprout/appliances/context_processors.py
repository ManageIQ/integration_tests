# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sprout import redis, settings


def hubber_url(request):
    return {'hubber_url': settings.HUBBER_URL}


def sprout_needs_update(request):
    return {"sprout_needs_update": redis._get("sprout-needs-update", default=False)}
