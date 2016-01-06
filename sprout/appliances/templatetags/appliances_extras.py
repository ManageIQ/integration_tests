# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True)
def progress(value):
    if isinstance(value, float):
        p = int(value * 100.0)
    else:
        p = value
    return mark_safe(r"""<div class='progress progress-striped'>
        <div class='progress-bar' style='width: {p}%;'>
        <span class='sr-only'>{p}% Complete</span></div></div>""".format(p=p))


@register.filter
def keyvalue(d, k):
    return d[k]
