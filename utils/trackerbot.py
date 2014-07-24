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


class ApiKeyAuth(object):
    """Auth type for using tastypie API keys in slumber"""
    def __init__(self, username, apikey):
        self.username = username.encode('ascii')
        self.apikey = apikey.encode('ascii')

    def __call__(self, request):
        request.headers['Authorization'] = 'ApiKey %s:%s' % (self.username, self.apikey)
        return request


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
    trackerbot_conf = env.get('trackerbot', {})
    url = trackerbot_conf.get('url')
    def_url = {'default': url, 'nargs': '?'} if url else {}

    username = trackerbot_conf.get('username')
    def_username = {'default': username, 'nargs': '?'} if username else {}

    apikey = trackerbot_conf.get('apikey')
    def_apikey = {'default': apikey, 'nargs': '?'} if apikey else {}

    parser = argparse.ArgumentParser()
    parser.add_argument('trackerbot_url',
        help='URL to the base of the tracker API, e.g. http://hostname/api/', **def_url)
    parser.add_argument('username',
        help='API username for authentication', **def_username)
    parser.add_argument('api_key',
        help='API key for authentication', **def_apikey)
    return parser


def api(trackerbot_url, username, api_key):
    """Return an API object authenticated to the given trackerbot api"""
    auth = ApiKeyAuth(username, api_key)
    return slumber.API(trackerbot_url, auth=auth)


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
