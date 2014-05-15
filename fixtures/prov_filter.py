from utils.conf import cfme_data
from utils.log import logger


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

filtered = ProviderFilter(cfme_data['management_systems'].keys())


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

    filtered_providers = cfme_data['management_systems'].keys()
    for provider in cfme_data['management_systems']:
        data = cfme_data['management_systems'][provider]
        tags = data.get('tags', [])
        if provider not in cmd_filter and not set(tags) & set(cmd_filter):
            filtered_providers.remove(provider)
    return filtered_providers
