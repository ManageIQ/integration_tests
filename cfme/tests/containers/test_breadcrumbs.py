from collections import namedtuple

import pytest

from cfme import test_requirements
from cfme.containers.image import Image
from cfme.containers.image_registry import ImageRegistry
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from cfme.containers.route import Route
from cfme.containers.service import Service
from cfme.containers.template import Template
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider_modscope'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='module'),
    test_requirements.containers
]


DataSet = namedtuple('DataSet', ['obj', 'collection_obj'])


TESTED_OBJECTS = [
    DataSet(Service, 'container_services'),
    DataSet(Route, 'container_routes'),
    DataSet(Project, 'container_projects'),
    DataSet(Pod, 'container_pods'),
    DataSet(Image, 'container_images'),
    DataSet(ContainersProvider, 'containers_providers'),
    DataSet(ImageRegistry, 'container_image_registries'),
    DataSet(Node, 'container_nodes'),
    DataSet(Replicator, 'container_replicators'),
    DataSet(Template, 'container_templates')
]


def clear_search(view):
    view.entities.search.clear_simple_search()
    view.entities.search.search_button.click()


def test_breadcrumbs(provider, appliance, soft_assert):

    """
    Polarion:
        assignee: juwatts
        caseimportance: high
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    for data_set in TESTED_OBJECTS:

        instances = ([provider] if data_set.collection_obj == 'containers_providers'
                     else getattr(appliance.collections, data_set.collection_obj).all())
        for instance in instances:
            if instance.exists:
                test_obj = instance
                break
        else:
            pytest.skip("No content found for test")

        view = navigate_to(test_obj, 'Details')

        soft_assert(view.breadcrumb.is_displayed,
                    'Breadcrumbs not found in {} {} summary page'
                    .format(data_set.obj.__name__, test_obj.name))

        soft_assert(view.summary_text in view.breadcrumb.locations,
            'Could not find breadcrumb "{}" in {} {} summary page. breadcrumbs: {}'
            .format(view.summary_text, view.breadcrumb.locations,
                    data_set.obj.__name__, test_obj.name))

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
                    name=test_obj.name, url=view.browser.url))
