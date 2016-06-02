import pytest
from cfme.middleware.datasource import MiddlewareDatasource
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_list_datasources():
    """Tests datasources list between UI, DB and Management system
    This test requires that no any other provider should exist before.

    Steps:
        * Get datasources list from UI
        * Get datasources list from Database
        * Get datasources list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_dses = _get_datasources_set(MiddlewareDatasource.datasources())
    db_dses = _get_datasources_set(MiddlewareDatasource.datasources_in_db())
    mgmt_dses = _get_datasources_set(MiddlewareDatasource.datasources_in_mgmt())
    assert ui_dses == db_dses == mgmt_dses, \
        ("Lists of datasources mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_dses, db_dses, mgmt_dses))


def test_list_provider_datasources(provider):
    """Tests datasources list from current Provider between UI, DB and Management system

    Steps:
        * Get datasources list from UI of provider
        * Get datasources list from Database of provider
        * Get datasources list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_dses = _get_datasources_set(MiddlewareDatasource.datasources(provider=provider))
    db_dses = _get_datasources_set(MiddlewareDatasource.datasources_in_db(provider=provider))
    mgmt_dses = _get_datasources_set(MiddlewareDatasource.datasources_in_mgmt(provider=provider))
    assert ui_dses == db_dses == mgmt_dses, \
        ("Lists of datasources mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_dses, db_dses, mgmt_dses))


def _get_datasources_set(datasources):
    """
    Return the set of datasources which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((datasource.name, datasource.server.name) for datasource in datasources)
