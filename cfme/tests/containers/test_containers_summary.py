import pytest
from cfme.containers.overview import ContainersOverview
from cfme.containers.provider import ContainersProvider
from cfme.web_ui import StatusBox
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('has_no_containers_providers'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


# CMP-9827 # CMP-9826 # CMP-9825 # CMP-9824 # CMP-9823 # CMP-9822 # CMP-9821 # CMP-9820
container_object_types = \
    ['routes', 'projects', 'container_images', 'image_registries',
     'container_services', 'containers', 'pods', 'nodes']
container_object_types_lowest = \
    ['routes', 'projects', 'images', 'image_registries',
     'services', 'containers', 'pods', 'nodes']


def test_containers_summary_objects(provider):
    """ Containers overview page > Widgets > Widgets summary
       This test checks that the amount of a selected object in the system is shown correctly
        in the widgets in the
       Overview menu
       Steps:
           * Goes to Compute --> Containers --> Overview
           * Checks how many objects are shown in the selected widget
           * Goes to Containers summary page and checks how many objects are shown there.
           * Checks the amount is equal
       """
    objects_key = ({
        version.LOWEST: container_object_types_lowest,
        '5.7': container_object_types
    })
    container_object = version.pick(objects_key)
    prov_ui_values, status_box_values = dict(), dict()
    navigate_to(ContainersOverview, 'All')
    for obj_type in container_object:
        status_box_values[obj_type] = StatusBox(obj_type).value()
    for obj_type in container_object:
        prov_ui_values[obj_type] = getattr(provider.summary.relationships, obj_type).value
        assert status_box_values[obj_type] == prov_ui_values[obj_type]
