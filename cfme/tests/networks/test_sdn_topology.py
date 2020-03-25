import random

import pytest

from cfme import test_requirements
from cfme.cloud.provider.azure import AzureProvider
from cfme.cloud.provider.ec2 import EC2Provider
from cfme.cloud.provider.gce import GCEProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [pytest.mark.provider([EC2Provider, AzureProvider, GCEProvider, OpenStackProvider],
                                   scope='module')]


@pytest.fixture(scope='module')
def elements_collection(setup_provider_modscope, appliance, provider):
    elements_collection_ = appliance.collections.network_topology_elements
    wait_for(elements_collection_.all, timeout=10)
    yield elements_collection_
    provider.delete_if_exists(cancel=False)
    provider.wait_for_delete()


@test_requirements.filtering
def test_topology_search(request, elements_collection):
    """Testing search functionality in Topology view.

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: gtalreja
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    elements = elements_collection.all()
    logger.info(str(elements))
    element_to_search = random.choice(elements)
    search_term = element_to_search.name[:len(element_to_search.name) // 2]
    elements_collection.search(search_term)
    request.addfinalizer(elements_collection.clear_search)
    for element in elements:
        logger.info(str(element))
        if search_term in element.name:
            assert not element.is_opaqued, (
                'Element should be not opaqued. Search: "{}", found: "{}"'.format(
                    search_term, element.name)
            )
        else:
            assert element.is_opaqued, (
                'Element should be opaqued. search: "{}", found: "{}"'.format(
                    search_term, element.name)
            )


@test_requirements.sdn
def test_topology_toggle_display(elements_collection):
    """Testing display functionality in Topology view.

    Metadata:
        test_flag: sdn

    Polarion:
        assignee: mmojzis
        casecomponent: WebUI
        initialEstimate: 1/4h
    """
    vis_terms = {True: 'Visible', False: 'Hidden'}
    for state in (True, False):
        for legend in elements_collection.legends:
            if state:
                elements_collection.disable_legend(legend)
            else:
                elements_collection.enable_legend(legend)
            for element in elements_collection.all():
                assert (
                    element.type != ''.join(legend.split()).rstrip('s') or
                    element.is_displayed != state
                ), (
                    'Element is {} but should be {} since "{}" display is currently {}'.format(
                        vis_terms[not state], vis_terms[state], legend,
                        {True: 'on', False: 'off'}[state])
                )
