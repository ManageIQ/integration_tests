#!/usr/bin/env python
"""Populate template tracker with information based on cfme_data"""
import sys
from collections import defaultdict
from threading import Lock, Thread

from slumber.exceptions import SlumberHttpBaseException

from utils import trackerbot
from utils.providers import list_all_providers, provider_factory


def main(trackerbot_url, mark_usable=None):
    api = trackerbot.api(trackerbot_url)

    thread_q = []
    thread_lock = Lock()
    template_providers = defaultdict(list)
    # Queue up list_template calls
    for provider_key in list_all_providers():
        thread = Thread(target=get_provider_templates,
            args=(provider_key, template_providers, thread_lock))
        thread_q.append(thread)
        thread.start()

    # Join the queued calls
    for thread in thread_q:
        thread.join()

    seen_templates = set()

    if mark_usable is None:
        usable = {}
    else:
        usable = {'usable': mark_usable}

    # Find some templates and update the API
    for template_name, providers in template_providers.items():
        try:
            stream, datestamp = trackerbot.parse_template(template_name)
        except (TypeError, ValueError):
            # No matches or template name was somehow not a string
            continue
        seen_templates.add(template_name)
        group = trackerbot.Group(stream)
        template = trackerbot.Template(template_name, group, datestamp)

        for provider_key in providers:
            provider = trackerbot.Provider(provider_key)

            try:
                trackerbot.mark_provider_template(api, provider, template, **usable)
                print 'Marked %s template %s on provider %s (Usable: %s, datestamp: %s)' % (
                    stream, template_name, provider_key, mark_usable, datestamp)
            except SlumberHttpBaseException as ex:
                print ex.response.status_code, ex.content

    # Remove templates that aren't on any providers anymore
    for template in api.template.get()['objects']:
        if template['name'] not in seen_templates:
            print "Cleaning up template %s on all providers" % template['name']
            api.template(template['name']).delete()

    # Remove provider relationships where they no longer exist
    for pt in api.providertemplate.get()['objects']:
        provider_key, template_name = pt['provider']['key'], pt['template']['name']
        if provider_key not in template_providers[template_name]:
            print "Cleaning up template %s on %s" % (template_name, provider_key)
            trackerbot.delete_provider_template(api, provider_key, template_name)


def get_provider_templates(provider_key, templates_providers, thread_lock):
    # functionalized to make it easy to farm this out to threads
    provider_mgmt = provider_factory(provider_key)
    try:
        templates = provider_mgmt.list_template()
        print provider_key, 'returned %d templates' % len(templates)
        with thread_lock:
            for template in templates:
                templates_providers[template].append(provider_key)
    except:
        print provider_key, 'failed'


def parse_cmdline():
    parser = trackerbot.cmdline_parser()
    parser.add_argument('--mark-usable', default=None, action='store_true',
        help="Mark all added templates as usable")
    args = parser.parse_args()
    return dict(args._get_kwargs())


if __name__ == '__main__':
    sys.exit(main(**parse_cmdline()))
