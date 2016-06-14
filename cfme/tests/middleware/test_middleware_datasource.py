from random import sample

import pytest
from cfme.middleware import get_random_list
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.server import MiddlewareServer
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 5  # when we have big list, limit number of items to test


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


def test_list_server_datasources():
    """Gets servers list and tests datasources list for each server
    Steps:
        * Get servers list from UI
        * Get datasources list from UI of server
        * Get datasources list from Database of server
        * Compare size of all the list [UI, Database]
    """
    servers = MiddlewareServer.servers()
    assert len(servers) > 0, "There is no server(s) available in UI"
    for server in get_random_list(servers, ITEMS_LIMIT):
        ui_dses = _get_datasources_set(MiddlewareDatasource.datasources(server=server))
        db_dses = _get_datasources_set(MiddlewareDatasource.datasources_in_db(server=server))
        assert ui_dses == db_dses, \
            ("Lists of datasources mismatch! UI:{}, DB:{}".format(ui_dses, db_dses))


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


def test_list_provider_server_datasources(provider):
    """Tests datasources list from current Provider for each server
    between UI, DB and Management system
    Steps:
        * Get servers list from UI of provider
        * Get datasources list for the server
        * Get datasources list from UI of provider, server
        * Get datasources list from Database of provider, server
        * Get datasources list from Database of provider, server
        * Get datasources list from Management system(Hawkular) of server
        * Compare size of all the list [UI, Database, Management system]
    """
    servers = MiddlewareServer.servers(provider=provider)
    assert len(servers) > 0, "There is no server(s) available in UI"
    for server in get_random_list(servers, ITEMS_LIMIT):
        ui_dses = _get_datasources_set(
            MiddlewareDatasource.datasources(provider=provider, server=server))
        db_dses = _get_datasources_set(
            MiddlewareDatasource.datasources_in_db(provider=provider, server=server))
        mgmt_dses = _get_datasources_set(
            MiddlewareDatasource.datasources_in_mgmt(provider=provider, server=server))
        assert ui_dses == db_dses == mgmt_dses, \
            ("Lists of datasources mismatch! UI:{}, DB:{}, MGMT:{}"
             .format(ui_dses, db_dses, mgmt_dses))


def test_datasource_details(provider):
    """Tests datasource details on UI

    Steps:
        * Get datasources list from UI
        * Select each datasource details in UI
        * Compare selected datasource UI details with CFME database and MGMT system
    """
    ds_list = MiddlewareDatasource.datasources(provider=provider)
    for ds in sample(ds_list, 1):
        ds_ui = ds.datasource(method='ui')
        ds_db = ds.datasource(method='db')
        ds_mgmt = ds_ui.datasource(method='mgmt')
        assert ds_ui, "Datasource was not found in UI"
        assert ds_db, "Datasource was not found in DB"
        assert ds_mgmt, "Datasource was not found in MGMT system"
        assert ds_ui.name == ds_db.name == ds_mgmt.name, \
            ("datasource name does not match between UI:{}, DB:{}, MGMT:{}"
             .format(ds_ui.name, ds_db.name, ds_mgmt.name))
        ds_db.validate_properties()
        ds_mgmt.validate_properties()


def _get_datasources_set(datasources):
    """
    Return the set of datasources which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((datasource.name, datasource.server.name) for datasource in datasources)
