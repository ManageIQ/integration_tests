import argparse
import json
import time
from collections import defaultdict
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests
import slumber

from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.providers import providers_data

session = requests.Session()
conf = env.get('trackerbot', {})
_active_streams = None


def cmdline_parser():
    """Get a parser with basic trackerbot configuration params already set up

    It will use the following keys from the env conf if they're available::

        # with example values
        trackerbot:
            url: http://hostname/api/
            username: username
            apikey: 0123456789abcdef

    """
    # Set up defaults from env, if they're set, otherwise require them on the commandline
    def_url = {'default': None, 'nargs': '?'} if 'url' in conf else {}

    parser = argparse.ArgumentParser()
    parser.add_argument('--trackerbot-url',
        help='URL to the base of the tracker API, e.g. http://hostname/api/', **def_url)
    return parser


def api(trackerbot_url=None):
    """Return an API object authenticated to the given trackerbot api"""
    if trackerbot_url is None:
        trackerbot_url = conf['url']

    return slumber.API(trackerbot_url, session=session)


def active_streams(api, force=False):
    global _active_streams
    if _active_streams is None or force:
        _active_streams = [stream['name'] for stream in api.group.get(stream=True)['objects']]
    return _active_streams


def provider_templates(api):
    provider_templates = defaultdict(list)
    for template in depaginate(api, api.template.get())['objects']:
        for provider in template['providers']:
            provider_templates[provider].append(template['name'])
    return provider_templates


def mark_provider_template(api, provider, template, tested=None, usable=None,
        diagnosis='', build_number=None, stream=None, custom_data=None):
    """Mark a provider template as tested and/or usable

    Args:
        api: The trackerbot API to act on
        provider: The provider's key in cfme_data or a :py:class:`Provider` instance
        template: The name of the template to mark on this provider or a :py:class:`Template`
        tested: Whether or not this template has been tested on this provider
        usable: Whether or not this template is usable on this provider
        diagnosis: Optional reason for marking a template

    Returns the response of the API request

    """
    provider_template = _as_providertemplate(provider, template, group=stream,
                                             custom_data=custom_data)

    if tested is not None:
        provider_template['tested'] = bool(tested)

    if usable is not None:
        provider_template['usable'] = bool(usable)

    if diagnosis:
        provider_template['diagnosis'] = diagnosis

    if build_number:
        provider_template['build_number'] = int(build_number)

    return api.providertemplate.post(provider_template)


def delete_provider_template(api, provider, template):
    """Delete a provider/template relationship, used when a template is removed from one provider"""
    provider_template = _as_providertemplate(provider, template)
    try:
        result = api.providertemplate(provider_template.concat_id).delete()
    except slumber.exceptions.HttpNotFoundError:
        logger.exception('Exception calling providertemplate.delete()')
        result = False
    if result:
        logger.info('Deleted providertemplate %s::%s', provider, template)
    else:
        logger.error('Delete call returned false for providertemplate %s::%s', provider, template)
    return result


def set_provider_active(api, provider, active=True):
    """Set a provider active (or inactive)

    Args:
        api: The trackerbot API to act on
        active: active flag to set on the provider (True or False)

    """
    api.provider[provider].patch(active=active)


def latest_template(api, group, provider_key=None):
    if not isinstance(group, Group):
        group = Group(str(group))

    if provider_key is None:
        # Just get the latest template for a given group, as well as its providers
        response = api.group(group['name']).get()
        return {
            'latest_template': response['latest_template'],
            'latest_template_providers': response['latest_template_providers'],
        }
    else:
        # Given a provider, use the provider API to get the latest
        # template for that provider, as well as the additional usable
        # providers for that template
        response = api.provider(provider_key).get()
        return response['latest_templates'][group['name']]


def templates_to_test(api, limit=1, request_type=None):
    """get untested templates to pass to jenkins

    Args:
        limit: max number of templates to pull per request
        request_type: request the provider_key of specific type
        e.g openstack

    """
    templates = []
    for pt in api.untestedtemplate.get(
            limit=limit, tested=False, provider__type=request_type).get(
            'objects', []):
        name = pt['template']['name']
        group = pt['template']['group']['name']
        provider = pt['provider']['key']
        request_type = pt['provider']['type']
        templates.append([name, provider, group, request_type])
    return templates


def get_tested_providers(api, template_name):
    """
    Return all tested provider templates for given template_name
    """
    response = api.providertemplate.get(tested=True, template=template_name, limit=200)
    providers = [pt['provider'] for pt in response.get('objects', []) if pt['provider']['active']]
    return providers


def mark_unusable_as_untested(api, template_name, provider_type):
    """
    Search through all tested providers and if provider type is unusable, mark it as not tested

    This action is limited to a specific template_name and a specific provider_type
    """
    # Get usable providers from template
    try:
        template = api.template(template_name).get()
        usable_providers = template['usable_providers']
    except slumber.exceptions.HttpNotFoundError:
        # Template doesn't even exist, nothing to do here
        return

    # Now find all tested provider templates. If they are tested BUT unusable, mark untested
    tested_providers = set(
        p['key'].lower() for p in get_tested_providers(api, template_name)
        if p['type'] == provider_type
    )

    tested_unusable_providers = [p for p in tested_providers if p not in usable_providers]

    for provider_key in tested_unusable_providers:
        mark_provider_template(api, provider_key, template_name, tested=False, usable=False)


def check_if_tested(api, template_name, provider_type):
    """
    Check if a template has been tested on a specific provider type.

    Args:
        template_name: e.g. "cfme-59021-02141929"
        provider_type: e.g. "rhevm"

    Returns:
        True if this template has been tested on at least one deployment of this provider type
        False otherwise
    """
    tested_providers = get_tested_providers(api, template_name)
    tested_types = set(p['type'].lower() for p in tested_providers)
    return provider_type.lower() in tested_types


def _as_providertemplate(provider, template, group=None, custom_data=None):
    if not isinstance(provider, Provider):
        provider = Provider(str(provider))
    if not isinstance(group, Group) and group is not None:
        group = Group(name=group)
    if not isinstance(template, Template):
        template = Template(str(template), group=group, custom_data=custom_data)

    return ProviderTemplate(provider, template)


def post_task_result(tid, result, output=None, coverage=0.0):
    if not output:
        output = "No output capture"
    api().task(tid).patch({'result': result, 'output': output, 'coverage': coverage})


def post_jenkins_result(job_name, number, stream, date, template, build_status, artifact_report):
    try:
        api().build.post({
            'job_name': job_name,
            'number': number,
            'stream': '/api/group/{}/'.format(stream),
            'datestamp': date,
            'template': template,
            'results': artifact_report,
        })
    except slumber.exceptions.HttpServerError as exc:
        print(exc.response)
        print(exc.content)


def add_provider_template(stream, provider, template_name, custom_data=None, mark_kwargs=None):
    """Checking existing providertemplates first, call mark_provider_template to add records

    Args:
        stream (str): build stream, like upstream or downstream-510z
        provider (str): provider key
        template_name (str): name of the template to track on provider
        custom_data (dict): JSON serializable custom data dict
        mark_kwargs (dict): Passed to mark_provider_template to allow for additional kwargs
    Returns:
        None on no action (already tracked)
        True on adding
        False on error
    """
    tb_api = api()
    try:
        existing_provider_templates = [
            pt['id']
            for pt in depaginate(
                tb_api,
                tb_api.providertemplate.get(provider=provider, template=template_name))['objects']]
        if '{}_{}'.format(template_name, provider) in existing_provider_templates:
            return None
        else:
            mark_provider_template(tb_api, provider, template_name, stream=stream,
                                   custom_data=custom_data, **(mark_kwargs or {}))
            return True
    except Exception:
        logger.exception('{}: Error occurred while template sync to trackerbot'.format(provider))
        return False


def depaginate(api, result):
    """Depaginate the first (or only) page of a paginated result"""
    meta = result['meta']
    if meta['next'] is None:
        # No pages means we're done
        return result

    # make a copy of meta that we'll mess with and eventually return
    # since we'll be chewing on the 'meta' object with every new GET
    # same thing for objects, since we'll just be appending to it
    # while we pull more records
    ret_meta = meta.copy()
    ret_objects = result['objects']
    while meta['next']:
        # parse out url bits for constructing the new api req
        next_url = urlparse(meta['next'])
        # ugh...need to find the word after 'api/' in the next URL to
        # get the resource endpoint name; not sure how to make this better
        next_endpoint = next_url.path.strip('/').split('/')[-1]
        next_params = {k: v[0] for k, v in parse_qs(next_url.query).items()}
        result = getattr(api, next_endpoint).get(**next_params)
        ret_objects.extend(result['objects'])
        meta = result['meta']

    # fix meta up to not tell lies
    ret_meta['total_count'] = len(ret_objects)
    ret_meta['next'] = None
    ret_meta['limit'] = ret_meta['total_count']
    return {
        'meta': ret_meta,
        'objects': ret_objects
    }


def composite_uncollect(build, source='jenkins', limit_ts=None):
    """Composite build function"""
    since = env.get('ts', time.time())
    params = {"build": build, "source": source, "since": since}
    if limit_ts:
        params['limit_ts'] = limit_ts
    try:
        resp = session.get(
            conf['ostriz'],
            params=params,
            timeout=(6, 60)  # 6s connect, 60s read
        )
        return resp.json()
    except Exception:
        logger.exception('Composite Uncollect hit an exception making request')
        return {'tests': []}


# Dict subclasses to help with JSON serialization
class Group(dict):
    """dict subclass to help serialize groups as JSON"""
    def __init__(self, name, stream=True, active=True):
        self.update({
            'name': name,
            'stream': stream,
            'active': active
        })


class Provider(dict):
    """dict subclass to help serialize providers as JSON"""
    def __init__(self, key):
        self['key'] = key
        # We assume this provider exists, is locally known, and has a type
        self['type'] = providers_data.get(key, {}).get('type')


class Template(dict):
    """dict subclass to help serialize templates as JSON"""
    def __init__(self, name, group=None, datestamp=None, custom_data=None):
        self['name'] = name
        if group is not None:
            self['group'] = group
        if datestamp is not None:
            self['datestamp'] = datestamp.strftime('%Y-%m-%d')

        if custom_data is not None:
            self['custom_data'] = json.dumps(custom_data)


class ProviderTemplate(dict):
    """dict subclass to help serialize providertemplate details as JSON"""
    def __init__(self, provider, template, usable=None, tested=None):
        self['provider'] = provider
        self['template'] = template

        if usable is not None:
            self['usable'] = bool(usable)

        if tested is not None:
            self['tested'] = bool(tested)

    @property
    def concat_id(self):
        return '_'.join([self['template']['name'], self['provider']['key']])
