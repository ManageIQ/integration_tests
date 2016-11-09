import pytest
from cfme.middleware import get_random_list
from cfme.middleware.datasource import MiddlewareDatasource
from utils import testgen
from utils.version import current_version
from deployment_methods import get_server
from deployment_methods import HAWKULAR_PRODUCT_NAME
from deployment_methods import EAP_PRODUCT_NAME
from datasource_methods import get_datasources_set
from datasource_methods import ORACLE_12C, DB2_105, MSSQL_2014, MYSQL_57
from datasource_methods import POSTGRESPLUS_94, POSTGRESQL_94, SYBASE_157

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 2  # when we have big list, limit number of items to test

DATASOURCES = [ORACLE_12C,
               DB2_105,
               MSSQL_2014,
               MYSQL_57,
               POSTGRESPLUS_94,
               POSTGRESQL_94,
               SYBASE_157]


def test_list_datasources():
    """Tests datasources list between UI, DB and Management system
    This test requires that no any other provider should exist before.

    Steps:
        * Get datasources list from UI
        * Get datasources list from Database
        * Get datasources list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_dses = get_datasources_set(MiddlewareDatasource.datasources())
    db_dses = get_datasources_set(MiddlewareDatasource.datasources_in_db())
    mgmt_dses = get_datasources_set(MiddlewareDatasource.datasources_in_mgmt())
    assert ui_dses == db_dses == mgmt_dses, \
        ("Lists of datasources mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_dses, db_dses, mgmt_dses))


def test_list_server_datasources(provider):
    """Gets servers list and tests datasources list for each server
    Steps:
        * Get Hawkular Local server
        * Get datasources list from UI of server
        * Get datasources list from Database of server
        * Compare size of all the list [UI, Database]
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_dses = get_datasources_set(MiddlewareDatasource.datasources(server=server))
    db_dses = get_datasources_set(MiddlewareDatasource.datasources_in_db(server=server))
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
    ui_dses = get_datasources_set(MiddlewareDatasource.datasources(provider=provider))
    db_dses = get_datasources_set(MiddlewareDatasource.datasources_in_db(provider=provider))
    mgmt_dses = get_datasources_set(MiddlewareDatasource.datasources_in_mgmt(provider=provider))
    assert ui_dses == db_dses == mgmt_dses, \
        ("Lists of datasources mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_dses, db_dses, mgmt_dses))


def test_list_provider_server_datasources(provider):
    """Tests datasources list from current Provider for each server
    between UI, DB and Management system
    Steps:
        * Get Hawkular Local server
        * Get datasources list for the server
        * Get datasources list from UI of provider, server
        * Get datasources list from Database of provider, server
        * Get datasources list from Database of provider, server
        * Get datasources list from Management system(Hawkular) of server
        * Compare size of all the list [UI, Database, Management system]
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_dses = get_datasources_set(
        MiddlewareDatasource.datasources(provider=provider, server=server))
    db_dses = get_datasources_set(
        MiddlewareDatasource.datasources_in_db(provider=provider, server=server))
    mgmt_dses = get_datasources_set(
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
    for ds in get_random_list(ds_list, ITEMS_LIMIT):
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


@pytest.mark.parametrize("datasource_params", DATASOURCES)
def test_create_delete_datasource(provider, datasource_params):
    """Tests datasource creation and deletion on EAP server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Invokes 'Add Datasource' toolbar operation
        * Selects Datasource type.
        * Click Next.
        * Input Datasource Name.
        * Input Datasource JNDI Name.
        * Click Next.
        * Input Driver Name.
        * Input Module Name.
        * Input Driver Name.
        * Input Driver Class.
        * Click Next.
        * Input Database Connection URL.
        * Input Database username.
        * Input Database password.
        * Submits the form.
        * Checks if newly created datasource is listed. Selects it.
        * Deletes that Datasource via UI operation.
        * Checks whether resource is deleted.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    server.add_datasource(datasource_params[0], datasource_params[1], datasource_params[2],
            datasource_params[3], datasource_params[4], datasource_params[5],
            datasource_params[6], datasource_params[7], datasource_params[8])
    # TODO uncomment when BZ#1383414 is fixes
    # resource = get_datasource_from_list(provider, datasource_params[1])
    # resource.delete()
    # check_datasource_not_listed(provider, datasource.name)
