PLUGIN_KEY = "upgraded-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # upgraded appliance type
    group.addoption('--use-upgraded-apps', action='store_true', default=False)
    group.addoption('--upgraded-apps-versions-from', default=[], action='append')
