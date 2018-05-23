from collections import namedtuple

import pytest

from cfme.containers.image import Image, ImageCollection
from cfme.containers.image_registry import (ImageRegistry,
                                            ImageRegistryCollection)
from cfme.containers.node import Node, NodeCollection
from cfme.containers.pod import Pod, PodCollection
from cfme.containers.project import Project, ProjectCollection
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator, ReplicatorCollection
from cfme.containers.route import Route, RouteCollection
from cfme.containers.service import Service, ServiceCollection
from cfme.containers.template import Template, TemplateCollection
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module')]


DataSet = namedtuple('DataSet', ['obj', 'collection_obj'])


TESTED_OBJECTS = [
    DataSet(Service, ServiceCollection),
    DataSet(Route, RouteCollection),
    DataSet(Project, ProjectCollection),
    DataSet(Pod, PodCollection),
    DataSet(Image, ImageCollection),
    DataSet(ContainersProvider, None),
    DataSet(ImageRegistry, ImageRegistryCollection),
    DataSet(Node, NodeCollection),
    DataSet(Replicator, ReplicatorCollection),
    DataSet(Template, TemplateCollection)
]


def clear_search(view):
    view.entities.search.clear_simple_search()
    view.entities.search.search_button.click()


@pytest.mark.polarion('CMP-10576')
def test_breadcrumbs(provider, appliance, soft_assert):

    """
    Polarion:
        assignee: None
        initialEstimate: None
    """
    for data_set in TESTED_OBJECTS:

        inst = (provider if data_set.obj is ContainersProvider
                else data_set.collection_obj(appliance).get_random_instances().pop())
        view = navigate_to(inst, 'Details')

        soft_assert(view.breadcrumb.is_displayed,
                    'Breadcrumbs not found in {} {} summary page'
                    .format(data_set.obj.__name__, inst.name))

        soft_assert(view.summary_text in view.breadcrumb.locations,
            'Could not find breadcrumb "{}" in {} {} summary page. breadcrumbs: {}'
            .format(view.summary_text, view.breadcrumb.locations,
                    data_set.obj.__name__, inst.name))

        view.breadcrumb.click_location(view.SUMMARY_TEXT)
        view = appliance.browser.create_view(data_set.obj.all_view)
        # We are doing this clear_search since when we navigate back from
        # [Details] page to [All] page via the breadcrumbs link it keeps the
        # previous search and then The title changes
        clear_search(view)

        soft_assert(view.is_displayed,
            'Breadcrumb link "{summary}" in {obj} {name} page should navigate to '
            '{obj}s all page. navigated instead to: {url}'
            .format(summary=view.summary_text, obj=data_set.obj.__name__,
                    name=inst.name, url=view.browser.url))
