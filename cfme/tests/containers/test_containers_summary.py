import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox
from utils import testgen
from utils.version import current_version
import time

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


# container_dashboard
# CMP-9827 # CMP-9826 # CMP-9825 # CMP-9824 # CMP-9823 # CMP-9822 # CMP-9821 # CMP-9820
SUMMARY_OBJECTS = \
    ['routes', 'projects', 'images', 'registries', 'services', 'containers', 'pods', 'nodes']


def test_containers_summary_objects(provider):
    """ Containers overview page > Widgets > Widget summary
       This test checks that the amount of a selected object in the system is shown correctly
        in the widgets in the
       Overview menu
       Steps:
           * Goes to Compute --> Containers --> Overview
           * Checks how many objects are shown in the selected widget
           * Goes to Containers summary page and checks how many objects are shown there.
           * Checks the amount is equal
       """
    sel.force_navigate('container_dashboard')
    sel.force_navigate('containers_provider', context={'provider': provider})
    routes_val = provider.summary.relationships.routes.value
    projects_val = provider.summary.relationships.projects.value
    images_val = provider.summary.relationships.images.value
    image_registries_val = provider.summary.relationships.image_registries.value
    services_val = provider.summary.relationships.services.value
    containers_val = provider.summary.relationships.containers.value
    pods_val = provider.summary.relationships.pods.value
    nodes_val = provider.summary.relationships.nodes.value
    for summary_object in SUMMARY_OBJECTS:
        sel.force_navigate('container_dashboard')
        time.sleep(2)
        amount = StatusBox(summary_object).value()
        if summary_object == 'routes':
            cont_val = routes_val
        elif summary_object == 'projects':
            cont_val = projects_val
        elif summary_object == 'images':
            cont_val = images_val
        elif summary_object == 'registries':
            cont_val = image_registries_val
        elif summary_object == 'services':
            cont_val = services_val
        elif summary_object == 'containers':
            cont_val = containers_val
        elif summary_object == 'pods':
            cont_val = pods_val
        elif summary_object == 'nodes':
            cont_val = nodes_val
        assert cont_val == amount
