# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe
from appliances.models import Appliance

from cfme.utils.timeutil import nice_seconds

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


@register.filter(is_safe=True)
def power_icon(power_state):
    if power_state not in Appliance.POWER_ICON_MAPPING:
        return power_state
    else:
        return mark_safe('<span class="glyphicon glyphicon-{}" title="{}"></span>'.format(
            Appliance.POWER_ICON_MAPPING[power_state], power_state))


@register.filter(is_safe=True)
def alert_type(tags):
    if tags == 'error':
        return mark_safe('danger')
    else:
        return mark_safe(tags)


@register.filter(is_safe=True)
def nice_timedelta(timedelta):
    try:
        return mark_safe(nice_seconds(timedelta.total_seconds()))
    except AttributeError:
        return mark_safe('None')


@register.filter
def user_repr(user):
    if user.first_name and user.last_name:
        return u' '.join([user.first_name, user.last_name])
    else:
        return user.username
