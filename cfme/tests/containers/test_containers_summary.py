import pytest
from widgetastic.utils import attributize_string

from cfme.containers.overview import ContainersOverview
from cfme.containers.provider import ContainersProvider
from cfme.containers.container import Container
from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.pod import Pod
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.web_ui import StatusBox

from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

# TODO Add Node back into the list when other classes are updated to use WT views and widgets.
tested_objects = [Service, Route, Project, Pod, Image, Container, ImageRegistry]


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
    navigate_to(ContainersOverview, 'All')
    # Collecting status boxes values:
    status_box_values = {obj: StatusBox(obj.PLURAL.split(' ')[-1]).value()
                         for obj in tested_objects}
    # Comparing to the values in the relationships tables:
    for obj in tested_objects:
        sb_val = status_box_values[obj]
        ui_val = getattr(provider.summary.relationships, attributize_string(obj.PLURAL)).value
        soft_assert(sb_val == ui_val,
            '{}: Mismatch between status box ({}) value in Containers overview'
            'and provider\'s relationships table ({}):'
            .format(obj.PLURAL, sb_val, ui_val))
