#!/usr/bin/env python
"""Populate template tracker with information based on cfme_data"""
import sys
import traceback
from collections import defaultdict
from threading import Lock, Thread

from slumber.exceptions import SlumberHttpBaseException

from utils import trackerbot, net
from utils.conf import cfme_data
from utils.providers import list_provider_keys, get_mgmt


def main(trackerbot_url, mark_usable=None):
    api = trackerbot.api(trackerbot_url)

    thread_q = []
    thread_lock = Lock()
    template_providers = defaultdict(list)
    all_providers = set(list_provider_keys())
    unresponsive_providers = set()
    # Queue up list_template calls
    for provider_key in all_providers:
        ipaddress = cfme_data['management_systems'][provider_key].get('ipaddress', None)
        if ipaddress and not net.is_pingable(ipaddress):
            continue
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

    existing_provider_templates = [
        pt['id']
        for pt
        in trackerbot.depaginate(api, api.providertemplate.get())['objects']]

    # Find some templates and update the API
    for template_name, providers in template_providers.items():
        template_name = str(template_name)

        group_name, datestamp, stream = trackerbot.parse_template(template_name)

        # Don't want sprout templates
        if group_name in ('sprout', 'rhevm-internal'):
            print('Ignoring {} from group {}'.format(template_name, group_name))
            continue

        seen_templates.add(template_name)
        group = trackerbot.Group(group_name, stream=stream)
        template = trackerbot.Template(template_name, group, datestamp)

        for provider_key in providers:
            provider = trackerbot.Provider(provider_key)

            if '{}_{}'.format(template_name, provider_key) in existing_provider_templates:
                print('Template {} already tracked for provider {}'.format(
                    template_name, provider_key))
                continue

            try:
                trackerbot.mark_provider_template(api, provider, template, **usable)
                print('Added {} template {} on provider {} (datestamp: {})'.format(
                    group_name, template_name, provider_key, datestamp))
            except SlumberHttpBaseException as ex:
                print("{}\t{}".format(ex.response.status_code, ex.content))

    # Remove provider relationships where they no longer exist, skipping unresponsive providers,
    # and providers not known to this environment
    for pt in trackerbot.depaginate(api, api.providertemplate.get())['objects']:
        provider_key, template_name = pt['provider']['key'], pt['template']['name']
        if provider_key not in template_providers[template_name] \
                and provider_key not in unresponsive_providers:
            if provider_key in all_providers:
                print("Cleaning up template {} on {}".format(template_name, provider_key))
                trackerbot.delete_provider_template(api, provider_key, template_name)
            else:
                print("Skipping template cleanup {} on unknown provider {}".format(
                    template_name, provider_key))

    # Remove templates that aren't on any providers anymore
    for template in trackerbot.depaginate(api, api.template.get())['objects']:
        if not template['providers']:
            print("Deleting template {} (no providers)".format(template['name']))
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
    try:
        with thread_lock:
            provider_mgmt = get_mgmt(provider_key)
        if cfme_data['management_systems'][provider_key]['type'] == 'ec2':
            # dirty hack to filter out ec2 public images, because there are literally hundreds.
            templates = provider_mgmt.api.get_all_images(owners=['self'],
                filters={'image-type': 'machine'})
            templates = map(lambda i: i.name or i.id, templates)
        else:
            templates = provider_mgmt.list_template()
        print(provider_key, 'returned {} templates'.format(len(templates)))
        with thread_lock:
            for template in templates:
                # If it ends with 'db', skip it, it's a largedb/nodb variant
                if str(template).lower().endswith('db'):
                    continue
                template_providers[template].append(provider_key)
    except:
        print("{}\t{}\t{}".format(provider_key, 'failed:', traceback.format_exc().splitlines()[-1]))
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
