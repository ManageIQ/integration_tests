import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import StatusBox
from utils import testgen
from utils.version import current_version
import time

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('has_no_container_providers'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')


# container_dashboard
# CMP-9827 # CMP-9826 # CMP-9825 # CMP-9824 # CMP-9823 # CMP-9822 # CMP-9821 # CMP-9820
container_object_types = \
    ['routes', 'projects', 'container_images', 'image_registries',
     'container_services', 'containers', 'pods', 'nodes']


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

    prov_ui_values = dict()
    for obj_type in container_object_types:
        prov_ui_values[obj_type] = getattr(provider.summary.relationships, obj_type).value

    sel.force_navigate('container_dashboard')
    time.sleep(2)
    for obj_type in container_object_types:
        assert StatusBox(obj_type).value() == prov_ui_values[obj_type]

