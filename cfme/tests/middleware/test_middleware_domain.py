import pytest
from cfme.middleware import get_random_list
from cfme.middleware.domain import MiddlewareDomain
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_domains():
    """Tests domains lists between UI, DB and Management system.

    Steps:
        * Get domains list from UI
        * Get domains list from Database
        * Get headers from UI
        * Compare headers from UI with expected headers list
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_domains = get_domains_set(MiddlewareDomain.domains())
    db_domains = get_domains_set(MiddlewareDomain.domains_in_db())
    mgmt_domains = get_domains_set(MiddlewareDomain.domains_in_mgmt())
    headers = MiddlewareDomain.headers()
    headers_expected = ['Domain Name', 'Feed', 'Provider']
    assert headers == headers_expected
    assert ui_domains == db_domains == mgmt_domains, \
        ("Lists of domains mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_domains, db_domains, mgmt_domains))


def test_list_provider_domains(provider):
    """Tests domains lists from current Provider between UI, DB and Management system

    Steps:
        * Get domains list from UI of provider
        * Get domains list from Database of provider
        * Get domains list from Management system(Hawkular)
        * Compare content of all the list [UI, Database, Management system]
    """
    ui_domains = get_domains_set(MiddlewareDomain.domains(provider=provider))
    db_domains = get_domains_set(MiddlewareDomain.domains_in_db(provider=provider))
    mgmt_domains = get_domains_set(MiddlewareDomain.domains_in_mgmt(provider=provider))
    assert ui_domains == db_domains == mgmt_domains, \
        ("Lists of domains mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_domains, db_domains, mgmt_domains))


def test_domain_details(provider):
    """Tests domain details on UI

    Steps:
        * Get domains list from UI
        * Select each domain details in UI
        * Compare selected domain UI details with CFME database and MGMT system
    """
    domain_list = MiddlewareDomain.domains(provider=provider)
    for domain in get_random_list(domain_list, 1):
        dmn_ui = domain.domain(method='ui')
        dmn_db = domain.domain(method='db')
        dmn_mgmt = domain.domain(method='mgmt')
        assert dmn_ui, "Domain was not found in UI"
        assert dmn_db, "Domain was not found in DB"
        assert dmn_mgmt, "Domain was not found in MGMT system"
        assert dmn_ui.name == dmn_db.name == dmn_mgmt.name, \
            ("domain name does not match between UI:{}, DB:{}, MGMT:{}"
             .format(dmn_ui.name, dmn_db.name, dmn_mgmt.name))
        dmn_db.validate_properties()
        dmn_mgmt.validate_properties()


def get_domains_set(domains):
    """
    Return the set of domains which contains only necessary fields,
    such as 'feed', 'provider.name' and 'name'
    """
    return set((domain.feed, domain.provider.name, domain.name)
               for domain in domains)
