from collections import OrderedDict

import pytest

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
    def __init__(self):
        # this gets populated in pytest_configure
        self.cmdline_filter = None
        # this gets populated on the first access to .providers
        self._providers = None

    @property
    def providers(self):
        if self._providers is None:
            self._providers = parse_filter(self.cmdline_filter)
            logger.debug('Filtering providers with {}, leaves {}'.format(
                self.cmdline_filter, self._providers))
        return self._providers

    def __contains__(self, provider):
        return provider in self.providers

filtered = ProviderFilter()


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--use-provider", action="append", default=[],
        help="list of providers or tags to include in test")


@pytest.mark.hookwrapper
def pytest_configure(config):
    # some other pytest_configure implementations try to access filtered.providers,
    # so wrap it and try to run before them
    filtered.cmdline_filter = config.getoption('use_provider') or ['default']
    assert filtered.cmdline_filter is not None
    yield


def parse_filter(cmdline_filter):
    """ Parse a list of command line filters and return a filtered set of providers.

    Args:
        cmdline_filter: A list of ``--use-provider`` options.
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
        if provider not in cmdline_filter and not set(tags) & set(cmdline_filter):
            filtered_providers.remove(provider)
    return filtered_providers
