from utils.log import logger
from utils.providers import global_filters, list_providers, ProviderFilter


def pytest_addoption(parser):
    # Create the cfme option group for use in other plugins
    parser.getgroup('cfme')
    parser.addoption("--use-provider", action="append", default=[],
        help="list of provider keys or provider tags to include in test")


def pytest_configure(config):
    """ Filters the list of providers as part of pytest configuration

    Note:
        Additional filter is added to the global_filters dict of active filters here.
    """

    cmd_filter = config.getvalueorskip('use_provider')
    if not cmd_filter:
        cmd_filter = ["default"]

    new_filter = ProviderFilter(keys=cmd_filter, required_tags=cmd_filter, conjunctive=False)
    global_filters['use_provider'] = new_filter

    logger.debug('Filtering providers with {}, leaves {}'.format(
        cmd_filter, [prov.key for prov in list_providers()]))
