import argparse
import re
import urlparse
from collections import defaultdict, namedtuple
from datetime import date
import urllib

import slumber
import requests

from utils.conf import env
from utils.providers import providers_data
from utils.version import get_stream


# regexen to match templates to streams and pull out the date
# stream names must be slugified (alphanumeric, dashes, underscores only)
# regex must include month and day, may include year
# If year is unset, will be the most recent month/day (not in the future)
stream_matchers = (
    (get_stream('latest'), '^miq-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.2'), r'^cfme-52.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.3'), r'^cfme-53.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.4'), r'^cfme-54.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.5'), r'^cfme-55.*-(?P<month>\d{2})(?P<day>\d{2})'),
    # Nightly builds are currently in the 5.4.z stream
    (get_stream('5.5'), r'^cfme-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
)
generic_matchers = (
    ('sprout', r'^s_tpl'),
    ('sprout', r'^sprout_template'),
    ('rhevm-internal', r'^auto-tmp'),
)
conf = env.get('trackerbot', {})
_active_streams = None

TemplateInfo = namedtuple('TemplateInfo', ['group_name', 'datestamp', 'stream'])


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

    return slumber.API(trackerbot_url)


def futurecheck(check_date):
    """Given a date object, return a date object that isn't from the future

    Some templates only have month/day values, not years. We create a date object

    """
    today = date.today()
    while check_date > today:
        check_date = date(check_date.year - 1, check_date.month, check_date.day)

    return check_date


def active_streams(api, force=False):
    global _active_streams
    if _active_streams is None or force:
        _active_streams = [stream['name'] for stream in api.group.get(stream=True)['objects']]
    return _active_streams


def parse_template(template_name):
    """Given a template name, attempt to extract its group name and upload date

    Returns:
        * None if no groups matched
        * group_name, datestamp of the first matching group. group name will be a string,
          datestamp with be a :py:class:`datetime.date <python:datetime.date>`, or None if
          a date can't be derived from the template name
    """
    for group_name, regex in stream_matchers:
        matches = re.match(regex, template_name)
        if matches:
            groups = matches.groupdict()
            # hilarity may ensue if this code is run right before the new year
            today = date.today()
            year = int(groups.get('year', today.year))
            month, day = int(groups['month']), int(groups['day'])
            # validate the template date by turning into a date obj
            template_date = futurecheck(date(year, month, day))
            return TemplateInfo(group_name, template_date, True)
    for group_name, regex in generic_matchers:
        matches = re.match(regex, template_name)
        if matches:
            return TemplateInfo(group_name, None, False)
    # If no match, unknown
    return TemplateInfo('unknown', None, False)


def provider_templates(api):
    provider_templates = defaultdict(list)
    for template in depaginate(api, api.template.get())['objects']:
        for provider in template['providers']:
            provider_templates[provider].append(template['name'])
    return provider_templates


def mark_provider_template(api, provider, template, tested=None, usable=None,
        diagnosis='', build_number=None):
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
    provider_template = _as_providertemplate(provider, template)

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
    return api.providertemplate(provider_template.concat_id).delete()


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


def _as_providertemplate(provider, template):
    if not isinstance(provider, Provider):
        provider = Provider(str(provider))
    if not isinstance(template, Template):
        template = Template(str(template))

    return ProviderTemplate(provider, template)


def post_task_result(tid, result, output=None):
    if not output:
        output = "No output capture"
    api().task(tid).put({'result': result, 'output': output})


def post_jenkins_result(job_name, number, stream, date, template,
        build_status, artifact_report):
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
        next_url = urlparse.urlparse(meta['next'])
        # ugh...need to find the word after 'api/' in the next URL to
        # get the resource endpoint name; not sure how to make this better
        next_endpoint = next_url.path.strip('/').split('/')[-1]
        next_params = {k: v[0] for k, v in urlparse.parse_qs(next_url.query).items()}
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


def composite_uncollect(build):
    """Composite build function"""

    url = "{}?build={}&source=jenkins".format(conf['ostriz'], urllib.quote(build))
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        print(e)
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
        self['type'] = providers_data[key]['type']


class Template(dict):
    """dict subclass to help serialize templates as JSON"""
    def __init__(self, name, group=None, datestamp=None):
        self['name'] = name
        if group is not None:
            self['group'] = group
        if datestamp is not None:
            self['datestamp'] = datestamp.strftime('%Y-%m-%d')


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
