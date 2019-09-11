#!/usr/bin/env python3
"""Populate template tracker with information based on cfme_data
uses Pool.starmap, which is py3 only
"""
import sys
from collections import defaultdict
from collections import namedtuple
from multiprocessing import Manager
from multiprocessing.pool import ThreadPool

from miq_version import TemplateName
from tabulate import tabulate
from wrapanapi import EC2System
from wrapanapi import Openshift

from cfme.utils import trackerbot
from cfme.utils.config_data import cfme_data
from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger
from cfme.utils.path import log_path
from cfme.utils.providers import get_mgmt

# manager for thread queues, instead of locking
manager = Manager()

ProvTemplate = namedtuple('ProvTemplate', 'provider_key, template_name')

GROUPS_TO_IGNORE = ('sprout', 'rhevm-internal', 'unknown')


def parse_cmdline():
    parser = trackerbot.cmdline_parser()
    parser.add_argument(
        '--mark-usable',
        default=None,
        action='store_true',
        help="Mark all added templates as usable",
    )
    parser.add_argument(
        '--provider-key',
        default=None,
        dest='selected_provider',
        nargs='*',
        help='A specific provider key to sync for',
    )
    parser.add_argument(
        '--outfile',
        dest='outfile',
        default=log_path.join('sync_template_tracker_report.log').strpath,
        help='Output file for tabulated reports on ProviderTemplate actions'
    )
    parser.add_argument(
        '--verbose',
        default=False,
        action='store_true',
        help='Log to stdout'
    )
    args = parser.parse_args()
    return dict(args._get_kwargs())


def main(trackerbot_url, mark_usable=None, selected_provider=None, **kwargs):
    tb_api = trackerbot.api(trackerbot_url)

    all_providers = set(
        selected_provider
        or [key for key, data in cfme_data.management_systems.items()
            if 'disabled' not in data.get('tags', [])])

    bad_providers = manager.Queue()
    # starmap the list of provider_keys into templates_on_provider
    # return is list of ProvTemplate tuples
    with ThreadPool(8) as pool:
        mgmt_templates = pool.starmap(
            templates_on_provider,
            ((provider_key, bad_providers) for provider_key in all_providers)
        )

    # filter out the misbehaving providers
    bad_provider_keys = []
    while not bad_providers.empty():
        bad_provider_keys.append(bad_providers.get())
    logger.warning('Filtering out providers that failed template query: %s', bad_provider_keys)
    working_providers = set([key for key in all_providers if key not in bad_provider_keys])

    # Flip mgmt_templates into dict keyed on template name, listing providers
    # [
    #   {prov1: [t1, t2]},
    #   {prov2: [t1, t3]},
    # ]
    #
    # mgmt_providertemplates should look like:
    # {
    #   t1: [prov1, prov2],
    #   t2: [prov1],
    #   t3: [prov2]
    # }
    mgmt_providertemplates = defaultdict(list)
    # filter out any empty results from pulling mgmt_templates
    for prov_templates in [mt for mt in mgmt_templates if mt is not None]:
        # expecting one key (provider), one value (list of templates)
        for prov_key, templates in prov_templates.items():
            for template in templates:
                mgmt_providertemplates[template].append(prov_key)

    logger.debug('DEBUG: template_providers: %r', mgmt_providertemplates)
    logger.debug('DEBUG: working_providers: %r', working_providers)

    usable = {'usable': mark_usable} if mark_usable is not None else {}

    # init these outside conditions/looping to be safe in reporting
    ignored_providertemplates = defaultdict(list)
    tb_pts_to_add = list()
    tb_pts_to_delete = list()
    tb_templates_to_delete = list()

    # ADD PROVIDERTEMPLATES
    # add all parseable providertemplates from what is actually on providers
    for template_name, provider_keys in mgmt_providertemplates.items():
        # drop empty names, or sprout groups
        # go over templates pulled from provider mgmt interfaces,
        if template_name.strip() == '':
            logger.info('Ignoring empty name template on providers %s', provider_keys)
        template_info = TemplateName.parse_template(template_name)
        template_group = template_info.group_name

        # Don't want sprout templates, or templates that aren't parsable cfme/MIQ
        if template_group in GROUPS_TO_IGNORE:
            ignored_providertemplates[template_group].append(template_name)
            continue

        tb_pts_to_add = [
            (template_group,
             provider_key,
             template_name,
             None,  # custom_data
             usable)
            for provider_key in provider_keys
        ]

        logger.info('Threading add providertemplate records to trackerbot for %s', template_name)

        with ThreadPool(8) as pool:
            # thread for each template, passing the list of providers with the template
            add_results = pool.starmap(
                trackerbot.add_provider_template,
                tb_pts_to_add
            )

    if not all([True if result in [None, True] else False for result in add_results]):
        # ignore results that are None, warn for any false results from adding
        logger.warning('Trackerbot providertemplate add failed, see logs')

    for group, names in ignored_providertemplates.items():
        logger.info('Skipped group [%s] templates %r', group, names)

    # REMOVE PROVIDERTEMPLATES
    # Remove provider relationships where they no longer exist, skipping unresponsive providers,
    # and providers not known to this environment
    logger.info('Querying providertemplate records from Trackerbot for ones to delete')
    pts = trackerbot.depaginate(
        tb_api,
        tb_api.providertemplate.get(provider_in=working_providers)
    )['objects']
    for pt in pts:
        key = pt['provider']['key']
        pt_name, pt_group = pt['template']['name'], pt['template']['group']['name']
        if pt_group in GROUPS_TO_IGNORE or key not in mgmt_providertemplates[pt_name]:
            logger.info("Marking trackerbot providertemplate for delete: %s::%s",
                        key, pt_name)
            tb_pts_to_delete.append(ProvTemplate(key, pt_name))

    with ThreadPool(8) as pool:
        # thread for each delete_provider_template call
        pool.starmap(
            trackerbot.delete_provider_template,
            ((tb_api, pt.provider_key, pt.template_name) for pt in tb_pts_to_delete))

    # REMOVE TEMPLATES
    # Remove templates that aren't on any providers anymore
    for template in trackerbot.depaginate(tb_api, tb_api.template.get())['objects']:
        template_name = template['name']
        if not template['providers'] and template_name.strip():
            logger.info("Deleting trackerbot template %s (no providers)", template_name)
            tb_templates_to_delete.append(template_name)
            tb_api.template(template_name).delete()

    # WRITE REPORT
    with open(kwargs.get('outfile'), 'a') as report:
        add_header = '##### ProviderTemplate records added: #####\n'
        del_header = '##### ProviderTemplate records deleted: #####\n'

        report.write(add_header)
        add_message = tabulate(
            sorted([(ptadd[0], ptadd[1], ptadd[2]) for ptadd in tb_pts_to_add],
                   key=lambda ptadd: ptadd[0]),
            headers=['Group', 'Provider', 'Template'],
            tablefmt='orgtbl'
        )
        report.write('{}\n\n'.format(add_message))
        report.write(del_header)
        del_message = tabulate(
            sorted([(ptdel.provider_key, ptdel.template_name) for ptdel in tb_pts_to_delete],
                   key=lambda ptdel: ptdel[0]),
            headers=['Provider', 'Template'],
            tablefmt='orgtbl'
        )
        report.write(del_message)
    logger.info('%s %s', add_header, add_message)
    logger.info('%s %s', del_header, del_message)
    return 0

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


def templates_on_provider(provider_key, bad_providers):
    """List templates on specific provider"""
    try:
        provider_mgmt = get_mgmt(provider_key)
        # TODO: change after openshift wrapanapi refactor
        templates = (
            provider_mgmt.list_template()
            if isinstance(provider_mgmt, Openshift)
            else [
                template.name
                for template in provider_mgmt.list_templates(
                    **({'executable_by_me': False} if isinstance(provider_mgmt, EC2System) else {})
                )
            ]
        )

        logger.info('%s returned %s templates', provider_key, len(templates))

        return {
            provider_key: [
                t for t in templates
                # If it ends with 'db', skip it, it's a largedb/nodb variant
                if not (t.lower().endswith('db') and not t.lower().endswith('extdb'))
            ]
        }

    except Exception:
        logger.exception('%s\t%s', provider_key, 'exception getting templates')
        bad_providers.put(provider_key)


if __name__ == '__main__':
    parsed_args = parse_cmdline()
    if parsed_args.get('verbose', False):
        add_stdout_handler(logger)
    sys.exit(main(**parsed_args))
