#!/usr/bin/env python
"""Populate template tracker with information based on cfme_data"""
import sys
from collections import defaultdict
from threading import Lock, Thread

from slumber.exceptions import SlumberHttpBaseException

from utils.providers import list_all_providers, provider_factory
from utils import trackerbot


def main(trackerbot_url, mark_usable=None):
    api = trackerbot.api(trackerbot_url)

    thread_q = []
    thread_lock = Lock()
    template_providers = defaultdict(list)
    # Queue up list_template calls
    for provider_key in list_all_providers():
        if provider_key.startswith('ec2') or provider_key.startswith('rhevm'):
            continue
        thread = Thread(target=get_provider_templates,
            args=(provider_key, template_providers, thread_lock))
        thread_q.append(thread)
        thread.start()

    # Join the queued calls
    for thread in thread_q:
        thread.join()

    # Find some templates and update the API
    for template_name, providers in template_providers.items():
        try:
            stream, datestamp = trackerbot.parse_template(template_name)
        except ValueError:
            # No matches
            continue
        group = trackerbot.Group(stream)
        template = trackerbot.Template(template_name, group, datestamp)

        for provider_key in providers:
            provider = trackerbot.Provider(provider_key)

            try:
                trackerbot.mark_provider_template(api, provider, template,
                    usable=mark_usable, tested=False)
                print 'template %s updated -- %s %s %r, marked usable: %s' % (
                    template, stream, datestamp, providers, bool(mark_usable))
            except SlumberHttpBaseException as ex:
                print ex.response.status_code, ex.content


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
