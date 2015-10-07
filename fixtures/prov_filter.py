from collections import OrderedDict
from utils.conf import cfme_data
from utils.log import logger
from utils.version import current_version


_version_operator_map = OrderedDict([('>=', lambda o, v: o >= v),
                                    ('<=', lambda o, v: o <= v),
                                    ('==', lambda o, v: o == v),
                                    ('!=', lambda o, v: o != v),
                                    ('>', lambda o, v: o > v),
                                     ('<', lambda o, v: o < v)])


def provider_keys():
    return cfme_data.get('management_systems', {}).keys()


class ProviderFilter(object):
    def __init__(self, defaults):
        self._filtered_providers = defaults

    @property
    def providers(self):
        return self._filtered_providers

    @providers.setter
    def providers(self, filtered):
        self._filtered_providers = parse_filter(filtered)

    def __contains__(self, provider):
        return provider in self.providers

filtered = ProviderFilter(provider_keys())


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--use-provider", action="append", default=[],
        help="list of providers or tags to include in test")


def pytest_configure(config):
    """ Filters the list of providers as part of pytest configuration. """

    cmd_filter = config.getvalueorskip('use_provider')
    if not cmd_filter:
        cmd_filter = ["default"]

    filtered.providers = cmd_filter

    logger.debug('Filtering providers with {}, leaves {}'.format(
        cmd_filter, filtered.providers))


def parse_filter(cmd_filter):
    """ Parse a list of command line filters and return a filtered set of providers.

    Args:
        cmd_filter: A list of ``--use-provider`` options.
    """

    filtered_providers = provider_keys()
    for provider in provider_keys():
        data = cfme_data['management_systems'][provider]
        restricted_version = data.get('restricted_version', None)
        if restricted_version:
            for op, comparator in _version_operator_map.items():
                # split string by op; if the split works, version won't be empty
                head, op, version = restricted_version.partition(op)
                if not version:
                    continue
                if not comparator(current_version(), version):
                    filtered_providers.remove(provider)
                break
            else:
                raise Exception('Operator not found in {}'.format(restricted_version))
        tags = data.get('tags', [])
        if provider not in cmd_filter and not set(tags) & set(cmd_filter):
            filtered_providers.remove(provider)
    return filtered_providers
