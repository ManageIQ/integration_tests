PLUGIN_KEY = "multi-region-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # multi-region appliance type
    group.addoption('--use-mr-apps', action='store_true', default=False,
                    dest='use-multi-region-apps')
    group.addoption('--num-mr-apps', action=1, type=int, dest='num-multi-region-apps')

    # some providers aren't suitable for multi-region tests due to issues with floating IP and etc
    group.addoption('--mr-apps-provider-type', default='rhevm',
                    dest='multi-region-apps-provider-type')
    group.addoption('--num-mr-apps-remote-nodes', action=1, type=int,
                    dest='num-multi-region-apps-remote-nodes')
