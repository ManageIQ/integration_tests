import pytest
from cfme.containers.overview import ContainersOverview
from cfme.containers.provider import ContainersProvider
from cfme.web_ui import StatusBox
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from utils.blockers import BZ

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


container_object_types = \
    ['routes', 'projects', 'container_images', 'image_registries',
     'container_services', 'containers', 'pods', 'nodes']
container_object_types_lowest = \
    ['routes', 'projects', 'images', 'image_registries',
     'services', 'containers', 'pods', 'nodes']
objects_key = ({
    version.LOWEST: container_object_types_lowest,
    '5.7': container_object_types
})


@pytest.mark.polarion('CMP-10575')
@pytest.mark.meta(blockers=[BZ(1441196)])
def test_containers_summary_objects(provider, soft_assert):
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
    container_object = version.pick(objects_key)
    prov_ui_values, status_box_values = dict(), dict()
    navigate_to(ContainersOverview, 'All')
    for obj_type in container_object:
        status_box_values[obj_type] = StatusBox(obj_type).value()
    for obj_type in container_object:
        prov_ui_values[obj_type] = getattr(provider.summary.relationships, obj_type).value
        soft_assert(status_box_values[obj_type] == prov_ui_values[obj_type],
            '{}: Mismatch between status box ({}) value in Containers overview'
            'and provider\'s relationships table ({}):'
            .format(obj_type, status_box_values[obj_type], prov_ui_values[obj_type]))
