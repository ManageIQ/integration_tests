import pytest

from cfme.middleware.provider import MiddlewareProvider
from cfme.utils import testgen
from cfme.utils import version
from cfme.utils.version import current_version
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.messaging import MiddlewareMessaging
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.deployment import MiddlewareDeployment


pytestmark = [
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([MiddlewareProvider], scope='function')

TOPOLOGY_TYPES = {"servers": {"MiddlewareServer"},
                  "deployments": {"MiddlewareDeployment",
                                  "MiddlewareDeploymentWar",
                                  "MiddlewareDeploymentEar"},
                  "datasources": {"MiddlewareDatasource"},
                  "messaging": {"MiddlewareMessaging"},
                  "vms": {"Vm"},
                  "containers": {"Container"},
                  "domains": {"MiddlewareDomain"},
                  "server_groups": {"MiddlewareServerGroup"}}


@pytest.mark.usefixtures('setup_provider')
def test_topology(provider):
    """Tests topology page from provider page

    Steps:
        * Get topology elements detail
        * Check number of providers on the page
        * Check number of `Servers`, `Domains`, `Messagings`,
        * `Datasources`, `Server Groups`, `Deployments` on topology page
    """

    # reload topology page to make sure all elements are loaded
    provider.topology.reload()
    provider.topology.refresh()

    assert len(provider.topology.elements(element_type='Hawkular')) == 1,\
        "More than one Hawkular providers found"

    assert provider.num_server(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareServer')), \
        "Number of server(s) miss match between topology page and in database"

    assert provider.num_messaging(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareMessaging')), \
        "Number of messaging(s) miss match between topology page and in database"

    assert provider.num_datasource(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDatasource')), \
        "Number of datasource(s) miss match between topology page and in database"

    assert provider.num_domain(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDomain')), \
        "Number of domain(s) miss match between topology page and in database"

    assert provider.num_server_group(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareServerGroup')), \
        "Number of server_group(s) miss match between topology page and in database"

    assert provider.num_deployment(method='db') == \
        len(provider.topology.elements(element_type='MiddlewareDeployment')) + \
        len(provider.topology.elements(element_type='MiddlewareDeploymentWar')) + \
        len(provider.topology.elements(element_type='MiddlewareDeploymentEar')),\
        "Number of deployment(s) miss match between topology page and in database"


@pytest.mark.uncollectif(current_version() != version.UPSTREAM)
@pytest.mark.usefixtures('setup_provider')
def test_topology_details(provider):
    """Tests items details in topology page from provider page

    Steps:
        * Get topology elements detail
        * Check details of `Servers`, `Domains`, `Messagings`,
        * `Datasources`, `Server Groups`, `Deployments` on topology page
    """

    # reload topology page to make sure all elements are loaded
    provider.topology.reload()
    provider.topology.refresh()

    verify_elements_match(MiddlewareServer.servers_in_db(),
                          provider.topology.elements(element_type='MiddlewareServer'))

    verify_elements_match(MiddlewareMessaging.messagings_in_db(),
                          provider.topology.elements(element_type='MiddlewareMessaging'))

    verify_elements_match(MiddlewareDatasource.datasources_in_db(),
                          provider.topology.elements(element_type='MiddlewareDatasource'))

    verify_elements_match(MiddlewareDomain.domains_in_db(),
                          provider.topology.elements(element_type='MiddlewareDomain'))

    server_groups = []
    for domain in MiddlewareDomain.domains_in_db():
        server_groups.extend(MiddlewareServerGroup.server_groups_in_db(domain))
    verify_elements_match(server_groups,
                          provider.topology.elements(element_type='MiddlewareServerGroup'))

    deployments = provider.topology.elements(element_type='MiddlewareDeployment')
    deployments.extend(provider.topology.elements(element_type='MiddlewareDeploymentWar'))
    deployments.extend(provider.topology.elements(element_type='MiddlewareDeploymentEar'))
    verify_elements_match(MiddlewareDeployment.deployments_in_db(), deployments)


@pytest.mark.usefixtures('setup_provider')
def test_topology_filter(provider):
    """Tests filters in topology page from provider page

    Steps:
        * Get topology elements detail
        * For each of `element types:
        * 1. filters them on topology page and verifies that they are hidden.
        * 2. selects them back and verify that it is shown in topology page.
    """

    # reload topology page to make sure all elements are loaded
    provider.topology.reload()
    provider.topology.refresh()

    for name, types in TOPOLOGY_TYPES.iteritems():
        show_all_types(provider.topology)
        hide_element_type(provider.topology, name)
        for type in types:
            verify_elements_hidden(provider.topology, type)
        show_element_type(provider.topology, name)
        for type in types:
            verify_elements_shown(provider.topology, type)


@pytest.mark.usefixtures('setup_provider')
def test_topology_server_hierarchy(provider):
    """Tests all server's hierarchical content in topology

    Steps:
        * Read Servers in topology.
        * For each server read elements in topology.
        * Compare elements from topology with server's elements from DB.
    """

    # reload topology page to make sure all elements are loaded
    provider.topology.reload()
    provider.topology.refresh()

    for ui_server in provider.topology.elements(element_type='MiddlewareServer'):
        elements = []
        server = MiddlewareServer.servers_in_db(name=ui_server.name)[0]
        elements.extend(MiddlewareDeployment.deployments_in_db(server, provider, strict=False))
        elements.extend(MiddlewareDatasource.datasources_in_db(server, provider, strict=False))
        elements.extend(MiddlewareMessaging.messagings_in_db(server, provider, strict=False))
        verify_elements_included(elements, ui_server.children)


def verify_elements_match(db_elements, ui_elements):
    db_elements_set = get_elements_set(db_elements)
    ui_elements_set = get_elements_set(ui_elements)
    assert db_elements_set == ui_elements_set, \
        ("Lists of elements mismatch! UI:{}, DB:{}"
         .format(ui_elements_set, db_elements_set))


def verify_elements_included(db_elements, ui_elements):
    """
    Verifies that elements from UI are all included in DB elements list.
    @todo: modify tolopogy.elements to return all elements
    in topology UI independent of element and line locations.
    """
    db_elements_set = get_elements_set(db_elements)
    ui_elements_set = get_elements_set(ui_elements)
    for ui_element in ui_elements_set:
        assert ui_element in db_elements_set, \
            ("UI element {} in not included in DB elements list {}"
             .format(ui_element, db_elements_set))


def verify_elements_hidden(topology, hidden_element_type):
    ui_elements = topology.elements(element_type=hidden_element_type)
    assert len(ui_elements) == 0, \
        'Element {} is visible in Topology, but should be hidden'.format(hidden_element_type)


def verify_elements_shown(topology, shown_element_type):
    ui_elements = topology.elements(element_type=shown_element_type)
    for element in ui_elements:
        assert not element.is_hidden, \
            'Element {} is hidden in Topology, but should shown'.format(element.name)


def get_elements_set(elements):
    """
    Return the set of elements which contains only necessary fields,
    such as 'name'
    """
    return set((element.name) for element in elements)


def hide_element_type(topology, hide_element_type):
    for legend in topology.legends:
        if legend == hide_element_type:
            getattr(topology, legend).set_active(active=False)
            break
    topology.refresh()


def show_element_type(topology, show_element_type):
    for legend in topology.legends:
        if legend == show_element_type:
            getattr(topology, legend).set_active(active=True)
            break
    topology.refresh()


def show_all_types(topology):
    for legend in topology.legends:
        if legend == show_element_type:
            getattr(topology, legend).set_active(active=True)
    topology.refresh()
