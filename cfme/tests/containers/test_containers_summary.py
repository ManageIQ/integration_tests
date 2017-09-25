import pytest

from cfme.containers.overview import ContainersOverview
from cfme.containers.provider import ContainersProvider
from cfme.containers.container import Container
from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.pod import Pod
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]

tested_objects = [Service, Route, Project, Pod, Image, Container, ImageRegistry, Node]


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
    view = navigate_to(ContainersOverview, 'All')
    # Collecting status boxes values:
    status_box_values = {obj: getattr(view, obj.PLURAL.split(' ')[-1].lower()).value
                         for obj in tested_objects}
    # Comparing to the values in the relationships tables:
    view = navigate_to(provider, 'Details')
    for obj in tested_objects:
        sb_val = status_box_values[obj]
        ui_val = int(view.entities.relationships.get_text_of(obj.PLURAL))
        soft_assert(sb_val == ui_val,
            '{}: Mismatch between status box ({}) value in Containers overview'
            'and provider\'s relationships table ({}):'
            .format(obj.PLURAL, sb_val, ui_val))
