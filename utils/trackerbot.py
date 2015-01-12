import argparse
import re
from datetime import date

import slumber

from utils.conf import env
from utils.version import get_stream


# regexen to match templates to streams and pull out the date
# stream names must be slugified (alphanumeric, dashes, underscores only)
# regex must include month and day, may include year
# If year is unset, will be the most recent month/day (not in the future)
stream_matchers = (
    (get_stream('master'), '^miq-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.2'), r'^cfme-52.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.3'), r'^cfme-53.*-(?P<month>\d{2})(?P<day>\d{2})'),
    # Nightly builds are currently in the 5.3.z stream
    (get_stream('5.3'), r'^cfme-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
)
trackerbot_conf = env.get('trackerbot', {})
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
    def_url = {'default': None, 'nargs': '?'} if 'url' in trackerbot_conf else {}

    parser = argparse.ArgumentParser()
    parser.add_argument('--trackerbot-url',
        help='URL to the base of the tracker API, e.g. http://hostname/api/', **def_url)
    return parser


def api(trackerbot_url=None):
    """Return an API object authenticated to the given trackerbot api"""
    if trackerbot_url is None:
        trackerbot_url = trackerbot_conf['url']

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
    """Given a template name, attempt to extract its stream name and upload date

    Returns:
        * None if no streams matched
        * stream, datestamp of the first matching stream. stream will be a string,
          datestamp with be a :py:class:`datetime.date <python:datetime.date>`
    """
    for stream, regex in stream_matchers:
        matches = re.match(regex, template_name)
        if matches:
            groups = matches.groupdict()
            # hilarity may ensue if this code is run right before the new year
            today = date.today()
            year = int(groups.get('year', today.year))
            month, day = int(groups['month']), int(groups['day'])
            # validate the template date by turning into a date obj
            template_date = futurecheck(date(year, month, day))
            return stream, template_date

    raise ValueError('No streams matched template %s' % template_name)


def mark_provider_template(api, provider, template, tested=None, usable=None, diagnosis=''):
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

    provider_template['diagnosis'] = diagnosis

    return api.providertemplate.post(provider_template)


def delete_provider_template(api, provider, template):
    """Delete a provider/template relationship, used when a template is removed from one provider"""
    provider_template = _as_providertemplate(provider, template)
    return api.providertemplate(provider_template.concat_id).delete()


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


def templates_to_test(api, limit=20):
    """get untested templates to pass to jenkins

    Args:
        limit: max number of templates to pull per request

    """
    templates = []
    for pt in api.providertemplate.get(limit=limit, tested=False).get('objects', []):
        name = pt['template']['name']
        group = pt['template']['group']['name']
        provider = pt['provider']['key']
        templates.append([name, provider, group])
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


def post_jenkins_result(job_name, number, stream, date, fails,
        skips, passes, template, build_status):
    api().build.post({
        'job_name': job_name,
        'number': number,
        'stream': '/api/group/{}/'.format(stream),
        'datestamp': date,
        'passes': passes,
        'fails': fails,
        'skips': skips,
        'template': template,
        'build_status': build_status,
    })


# Dict subclasses to help with JSON serialization
class Group(dict):
    """dict subclass to help serialize groups as JSON"""
    def __init__(self, name):
        self['name'] = name


class Provider(dict):
    """dict subclass to help serialize providers as JSON"""
    def __init__(self, key):
        self['key'] = key


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
