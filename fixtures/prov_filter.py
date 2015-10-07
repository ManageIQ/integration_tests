from utils.conf import cfme_data
from utils.log import logger


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
        tags = data.get('tags', [])
        if provider not in cmd_filter and not set(tags) & set(cmd_filter):
            filtered_providers.remove(provider)
    return filtered_providers
