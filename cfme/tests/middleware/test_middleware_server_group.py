import pytest
from cfme.middleware import get_random_list
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")

ITEMS_LIMIT = 5  # when we have big list, limit number of items to test


def test_list_provider_server_groups(provider):
    """Tests server groups lists from current Provider between UI, DB and Management system

    Steps:
        * Get domains list from UI of provider
        * Chooses one of domains
        * Get server groups list from UI of domain
        * Get server groups list from Database of domain
        * Get server groups list from Management system(Hawkular)
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    domain_list = MiddlewareDomain.domains(provider=provider)
    for domain in get_random_list(domain_list, 1):
        ui_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups(domain=domain))
        db_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups_in_db(domain=domain))
        mgmt_server_groups = get_server_group_set(
            MiddlewareServerGroup.server_groups_in_mgmt(domain=domain))
        headers = MiddlewareServerGroup.headers(domain)
        headers_expected = ['Server Group Name', 'Feed', 'Domain Name', 'Profile']
        assert headers == headers_expected
        assert ui_server_groups == db_server_groups == mgmt_server_groups, \
            ("Lists of server groups mismatch! UI:{}, DB:{}, MGMT:{}"
             .format(ui_server_groups, db_server_groups, mgmt_server_groups))


def test_server_group_details(provider):
    """Tests server group details on UI

    Steps:
        * Get domains list from UI of provider
        * Chooses one of domains
        * Get server groups list from UI of domain
        * Chooses several server groups from list
        * Select each server group's details in UI, DB and MGMT
        * Compare selected server group UI details with CFME database and MGMT system
    """
    domain_list = MiddlewareDomain.domains(provider=provider)
    for domain in get_random_list(domain_list, ITEMS_LIMIT):
        server_group_list = MiddlewareServerGroup.server_groups(domain=domain)
        for server_group in get_random_list(server_group_list, 1):
            svgr_ui = server_group.server_group(method='ui')
            svgr_db = server_group.server_group(method='db')
            svgr_mgmt = server_group.server_group(method='mgmt')
            assert svgr_ui, "Server Group was not found in UI"
            assert svgr_db, "Server Group was not found in DB"
            assert svgr_mgmt, "Server Group was not found in MGMT system"
            assert svgr_ui.name == svgr_db.name == svgr_mgmt.name, \
                ("Server Group name does not match between UI:{}, DB:{}, MGMT:{}"
                 .format(svgr_ui.name, svgr_db.name, svgr_mgmt.name))
            svgr_db.validate_properties()
            svgr_mgmt.validate_properties()


def get_server_group_set(server_groups):
    """
    Return the set of server groups which contains only necessary fields,
    such as 'feed', 'domain.name', 'name' and 'profile'
    """
    return set((server_group.feed, server_group.domain.name, server_group.name,
                server_group.profile)
               for server_group in server_groups)
