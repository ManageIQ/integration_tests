PLUGIN_KEY = "regular-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # regular appliance type
    group.addoption('--no-regular-apps', action='store_false', default=True)
    group.addoption('--num-regular-apps', action=1, type=int)
