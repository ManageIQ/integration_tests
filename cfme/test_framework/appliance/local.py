PLUGIN_KEY = "local-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # dev/local appliance type
    group.addoption('--use-local-apps', action='store_true', default=False)
