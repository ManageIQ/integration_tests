# -*- coding: utf-8 -*-
from sprout import settings


def hubber_url(request):
    return {'hubber_url': settings.HUBBER_URL}
