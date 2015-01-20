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
    providers = set(list_all_providers())
    unresponsive_providers = set()
    # Queue up list_template calls
    for provider_key in providers:
        thread = Thread(target=get_provider_templates,
            args=(provider_key, template_providers, unresponsive_providers, thread_lock))
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

    existing_provider_templates = [pt['id'] for pt in api.providertemplate.get(limit=0)['objects']]

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
            if '{}_{}'.format(template_name, provider_key) in existing_provider_templates:
                print 'Template %s already exists on on provider %s' % (template_name, provider_key)
                continue

            try:
                trackerbot.mark_provider_template(api, provider, template, **usable)
                print 'Added %s template %s on provider %s (datestamp: %s)' % (
                    stream, template_name, provider_key, datestamp)
            except SlumberHttpBaseException as ex:
                print ex.response.status_code, ex.content

    # Remove provider relationships where they no longer exist, skipping unresponsive providers
    for pt in api.providertemplate.get(limit=0)['objects']:
        provider_key, template_name = pt['provider']['key'], pt['template']['name']
        if provider_key not in template_providers[template_name] \
                and provider_key not in unresponsive_providers:
            print "Cleaning up template %s on %s" % (template_name, provider_key)
            trackerbot.delete_provider_template(api, provider_key, template_name)

    # Remove templates that aren't on any providers anymore
    for template in api.template.get(limit=0)['objects']:
        if not template['providers']:
            print "Deleting template %s (no providers)" % template['name']
            api.template(template['name']).delete()

    # This is included in case we ever want it, but for now I think it's better to handle this
    # manually, mainly due to the unreliability of the rhevm providers. Also, we may want to mark
    # a functional provider as inactive, but this script won't care and will flip it back to
    # active just for fun, which we might not want.
    # # Set provider active flag if needed
    # for provider in api.provider.get(limit=0)['objects']:
    #     # Only check providers that we know about
    #     if provider['key'] in providers:
    #         # If the provider was unresponsive and it listed as active, deactivate it
    #         if provider['key'] in unresponsive_providers and provider['active']:
    #             trackerbot.set_provider_active(False)
    #         # Likewise, if the provider was responsive and is listed as inactive, activate it
    #         elif provider['key'] not in unresponsive_providers and not provider['active']:
    #             trackerbot.set_provider_active(True)


def get_provider_templates(provider_key, template_providers, unresponsive_providers, thread_lock):
    # functionalized to make it easy to farm this out to threads
    provider_mgmt = provider_factory(provider_key)
    try:
        templates = provider_mgmt.list_template()
        print provider_key, 'returned %d templates' % len(templates)
        with thread_lock:
            for template in templates:
                # If it ends with 'db', skip it, it's a largedb/nodb variant
                if str(template).lower().endswith('db'):
                    continue
                template_providers[template].append(provider_key)
    except:
        print provider_key, 'failed'
        with thread_lock:
            unresponsive_providers.add(provider_key)


def parse_cmdline():
    parser = trackerbot.cmdline_parser()
    parser.add_argument('--mark-usable', default=None, action='store_true',
        help="Mark all added templates as usable")
    args = parser.parse_args()
    return dict(args._get_kwargs())


if __name__ == '__main__':
    sys.exit(main(**parse_cmdline()))
