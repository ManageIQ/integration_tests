PLUGIN_KEY = "pod-appliance"


def pytest_addoption(parser):
    group = parser.getgroup("cfme")

    # pod appliance type
    group.addoption('--use-pod-apps', action='store_true', default=False)
    group.addoption('--num-pod-apps', action=1, type=int)
    # todo: add below options
    # --sprout-template-type=openshift_pod
    # --sprout-ignore-preconfigured
