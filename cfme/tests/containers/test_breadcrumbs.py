from collections import namedtuple

import pytest

from cfme.containers.service import Service
from cfme.containers.route import Route
from cfme.containers.project import Project
from cfme.containers.pod import Pod
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.image import Image
from cfme.containers.node import Node
from cfme.containers.replicator import Replicator
from cfme.containers.template import Template
from cfme.containers.volume import Volume
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.usefixtures('has_persistent_volume'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module')]


DataSet = namedtuple('DataSet', ['obj', 'allView'])


TESTED_OBJECTS = [
    Service, Route, Project, Pod, Image, ContainersProvider, ImageRegistry,
    Node, Replicator, Template, Volume
]


@pytest.mark.polarion('CMP-10576')
def test_breadcrumbs(provider, appliance, soft_assert):

    for obj in TESTED_OBJECTS:

        inst = (provider if obj is ContainersProvider
                else obj.get_random_instances(provider, 1, appliance).pop())
        view = navigate_to(inst, 'Details')

        soft_assert(view.breadcrumb.is_displayed,
                    'Breadcrumbs not found in {} {} summary page'
                    .format(obj.__name__, inst.name))

        soft_assert(obj.all_view.SUMMARY_TEXT in view.breadcrumb.locations,
            'Could not find breadcrumb "{}" in {} {} summary page. breadcrumbs: {}'
            .format(obj.all_view.SUMMARY_TEXT, view.breadcrumb.locations,
                    obj.__name__, inst.name))

        view.breadcrumb.click_location(obj.all_view.SUMMARY_TEXT)
        view = appliance.browser.create_view(obj.all_view)

        soft_assert(view.is_displayed,
            'Breadcrumb link "{summary}" in {obj} {name} page should navigate to '
            '{name}s main page. navigated instead to: {url}'
            .format(summary=obj.all_view.SUMMARY_TEXT, obj=obj.__name__,
                    name=inst.name, url=view.browser.url))
