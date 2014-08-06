import argparse
import re
from datetime import date

import slumber

from utils.conf import env

# regexen to match templates to streams and pull out the date
# stream names must be slugified (alphanumeric, dashes, underscores only)
# regex must include month and day, may include year
# If year is unset, will be the most recent month/day (not in the future)
stream_matchers = (
    ('upstream', '^miq-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    ('downstream-52z', r'^cfme-52.*-(?P<month>\d{2})(?P<day>\d{2})'),
    ('downstream-53z', r'^cfme-53.*-(?P<month>\d{2})(?P<day>\d{2})'),
    # Nightly builds are currently in the 5.3.z stream
    ('downstream-53z', r'^cfme-nightly-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
)
trackerbot_conf = env.get('trackerbot', {})


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
    parser.add_argument('trackerbot_url',
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


def mark_provider_template(api, provider, template, tested=None, usable=None):
    """Mark a provider template as tested and/or usable

    Args:
        api: The trackerbot API to act on
        provider: The provider's key in cfme_data or a :py:class:`Provider` instance
        template: The name of the template to mark on this provider or a :py:class:`Template`
        tested: Whether or not this template has been tested on this provider
        usable: Whether or not this template is usable on this provider

    Returns the response of the API request

    """
    if not isinstance(provider, Provider):
        provider = Provider(str(provider))
    if not isinstance(template, Template):
        template = Template(str(template))

    provider_template = ProviderTemplate(provider, template)

    if tested is not None:
        provider_template['tested'] = bool(tested)

    if usable is not None:
        provider_template['usable'] = bool(usable)

    return api.providertemplate.post(provider_template)


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
    def __init__(self, name, group, datestamp):
        self['name'] = name
        self['group'] = group
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
