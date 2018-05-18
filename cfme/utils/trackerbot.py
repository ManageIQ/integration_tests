import argparse
import json
import re
import six.moves.urllib.parse
import six.moves.urllib.request
import six.moves.urllib.error
from collections import defaultdict, namedtuple
from datetime import date, datetime

import attr
import slumber
import requests
from lxml import html
import time

from cfme.utils.conf import env
from cfme.utils.log import logger
from cfme.utils.providers import providers_data
from cfme.utils.version import get_stream


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
    (get_stream('5.6'), r'^cfme-56.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.7'), r'^cfme-57.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.8'), r'^cfme-58.*-(?P<month>\d{2})(?P<day>\d{2})'),
    (get_stream('5.9'), r'^cfme-59.*-(?P<month>\d{2})(?P<day>\d{2})'),
    ('upstream_stable', r'^miq-stable-(?P<release>gapri[-\w]*?)'  # release name limit to 5 chars
                        r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    ('upstream_euwe', r'^miq-stable-(?P<release>euwe[-\w]*?)'
                      r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    ('upstream_fine', r'^miq-stable-(?P<release>fine[-\w]*?)'
                      r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),
    # new format, TODO remove with TemplateName update, no more CFME nightly
    ('downstream-nightly', r'^cfme-nightly-\d*-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})'),

    # Regex for standardized dates using TemplateName class below
    # TODO swap these in when TemplateName is in use
    # (get_stream('5.7'), r'^cfme-57.*-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})')
    # (get_stream('5.8'), r'^cfme-58.*-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})')
    # (get_stream('5.9'), r'^cfme-59.*-(?P<year>\d{4})?(?P<month>\d{2})(?P<day>\d{2})')
    # Nightly builds have potentially multiple version streams bound to them so we
    # cannot use get_stream()
    # ('upstream_stable', r'^miq-(?P<release>gapri[-\w]*?)'
    #                    r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})')
    # ('upstream_euwe', r'^miq-(?P<release>euwe[-\w]*?)'
    #                  r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})')
    # ('upstream_fine', r'^miq-(?P<release>fine[-\w]*?)'
    #                  r'-(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})')

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
            try:
                # year, month, day might have been parsed incorrectly with loose regex
                template_date = futurecheck(date(year, month, day))
            except ValueError:
                logger.exception('Failed to parse year: %s, month: %s, day: %s correctly '
                                 'from template %s with regex %s',
                                 year, month, day, template_name, regex)
                continue
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


def trackerbot_add_provider_template(stream, provider, template_name, custom_data=None):
    try:
        existing_provider_templates = [
            pt['id']
            for pt in depaginate(
                api(), api().providertemplate.get(provider=provider))['objects']]
        if '{}_{}'.format(template_name, provider) in existing_provider_templates:
            print('Template {} already tracked for provider {}'.format(
                template_name, provider))
        else:
            mark_provider_template(api(), provider, template_name, stream=stream,
                                   custom_data=custom_data)
            print('Added {} template {} on provider {}'.format(
                stream, template_name, provider))
    except Exception as e:
        print(e)
        print('{}: Error occured while template sync to trackerbot'.format(provider))


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
        next_url = six.moves.urllib.parse.urlparse(meta['next'])
        # ugh...need to find the word after 'api/' in the next URL to
        # get the resource endpoint name; not sure how to make this better
        next_endpoint = next_url.path.strip('/').split('/')[-1]
        next_params = {k: v[0] for k, v in six.moves.urllib.parse.parse_qs(next_url.query).items()}
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


def composite_uncollect(build, source='jenkins'):
    """Composite build function"""
    since = env.get('ts', time.time())
    url = "{0}?build={1}&source={2}&since={3}".format(
        conf['ostriz'],
        six.moves.urllib.parse.quote(build),
        six.moves.urllib.parse.quote(source),
        six.moves.urllib.parse.quote(since))
    try:
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        print(e)
        return {'tests': []}


@attr.s
class TemplateName(object):
    """Generate a template name from given link, a timestamp, and optional version string

    This method should handle naming templates from the following URL types:

    - http://<build-server-address>/builds/manageiq/master/latest/
    - http://<build-server-address>/builds/manageiq/gaprindashvili/stable/
    - http://<build-server-address>/builds/manageiq/fine/stable/
    - http://<build-server-address>/builds/cfme/5.8/stable/
    - http://<build-server-address>/builds/cfme/5.9/latest/

    These builds fall into a few categories:

    - MIQ nightly (master/latest)  (upstream)
    - MIQ stable (<name>/stable)  (upstream_stable, upstream_fine, etc)
    - CFME nightly (<stream>/latest)  (downstream-nightly)
    - CFME stream (<stream>/stable)  (downstream-<stream>)

    The generated template names should follow the syntax with 5 digit version numbers:

    - MIQ nightly: miq-nightly-<yyyymmdd>  (miq-nightly-201711212330)
    - MIQ stable: miq-<name>-<number>-yyyymmdd  (miq-fine-4-20171024, miq-gapri-20180130)
    - CFME nightly: cfme-nightly-<version>-<yyyymmdd>  (cfme-nightly-59000-20170901)
    - CFME stream: cfme-<version>-<yyyymmdd>  (cfme-57402-20171202)

    Release names for upstream will be truncated to 5 letters (thanks gaprindashvili...)
    """
    SHA = 'SHA256SUM'
    CFME_ID = 'cfme'
    MIQ_ID = 'manageiq'
    build_url = attr.ib()  # URL to the build folder with ova/vhd/qc2/etc images

    @property
    def build_version(self):
        """Version string from version file in build folder (cfme)
        release name and build number from an image file (MIQ)

        Will substitute 'nightly' for master URLs

        Raises:
            ValueError if unable to parse version string or release name from files

        Returns:
            String 5-digit version number or release name for MIQ
        """
        v = requests.get('/'.join([self.build_url, 'version']))
        if v.ok:
            logger.info('version file found, parsing dotted version string')
            match = re.search(
                '^(?P<major>\d)\.?(?P<minor>\d)\.?(?P<patch>\d)\.?(?P<build>\d{1,2})',
                v.content)
            if match:
                return ''.join([match.group('major'),
                                match.group('minor'),
                                match.group('patch'),
                                match.group('build').zfill(2)])  # zero left-pad
            else:
                raise ValueError('Unable to match version string in %s/version: {}'
                                 .format(self.build_url, v.content))
        else:
            logger.info('No version file found in %s, pulling build name from image file',
                        self.build_url)
            build_dir = requests.get(self.build_url)
            link_parser = html.fromstring(build_dir.content)
            # Find image file links, use first one to pattern match name
            # iterlinks returns tuple of (element, attribute, link, position)
            images = [l
                      for _, a, l, _ in link_parser.iterlinks()
                      if a == 'href' and l.endswith('.ova') or l.endswith('.vhd')]
            if images:
                # pull release and its possible number (with -) from image string
                # examples: miq-prov-fine-4-date-hash.vhd, miq-prov-gaprindashvilli-date-hash.vhd
                match = re.search(
                    'manageiq-(?:[\w]+?)-(?P<release>[\w]+?)(?P<number>-\d)?-\d{''3,}',
                    str(images[0]))
                if match:
                    # if its a master image, version is 'nightly', otherwise use release+number
                    return ('nightly'
                            if 'master' in match.group('release')
                            else '{}{}'.format(match.group('release')[:5], match.group('number')))
                else:
                    raise ValueError('Unable to match version string in image file: {}'
                                     .format(images[0]))
            else:
                raise ValueError('No image of ova or vhd type found to parse version from in {}'
                                 .format(self.build_url))

    @property
    def build_date(self):
        """Get a build date from the SHA256SUM"""
        r = requests.get('/'.join([self.build_url, self.SHA]))
        if r.ok:
            timestamp = datetime.strptime(r.headers.get('Last-Modified'),
                                          "%a, %d %b %Y %H:%M:%S %Z")
            return timestamp.strftime('%Y%m%d')
        else:
            raise ValueError('{} file not found in {}'.format(self.SHA, self.build_url))

    @property
    def template_name(self):
        """Actually construct the template name"""
        return '-'.join([self.CFME_ID if self.CFME_ID in self.build_url else self.MIQ_ID,
                         self.build_version,
                         self.build_date])


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
