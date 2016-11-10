import pytest

from utils import testgen
from utils.version import current_version
from deployment_methods import get_server
from deployment_methods import EAP_PRODUCT_NAME
from jdbc_driver_methods import download_jdbc_driver, deploy_jdbc_driver
from jdbc_driver_methods import ORACLE_12C_JDBC, DB2_105_JDBC, MSSQL_2014_JDBC, MYSQL_57_JDBC
from jdbc_driver_methods import POSTGRESPLUS_94_JDBC, POSTGRESQL_94_JDBC, SYBASE_157_JDBC

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 5  # when we have big list, limit number of items to test

DATABASES = [ORACLE_12C_JDBC,
             DB2_105_JDBC,
             MSSQL_2014_JDBC,
             MYSQL_57_JDBC,
             POSTGRESPLUS_94_JDBC,
             POSTGRESQL_94_JDBC,
             SYBASE_157_JDBC]


@pytest.mark.parametrize("database_params", DATABASES)
def test_deploy_driver(provider, database_params):
    """Tests Deployment of provided JDBC Driver into EAP7 server

    Steps:
        * Get servers list from UI
        * Chooses JBoss EAP server from list
        * Invokes 'Add JDBC Driver' toolbar operation
        * Selects JDBC driver file to upload.
        * Input Driver Name.
        * Input Module Name.
        * Input Driver Name.
        * Input Driver Class.
        * Input Major Version.
        * Input Minor Version.
        * Submits the form.
        * Checks that notification message is shown.
    """
    server = get_server(provider, EAP_PRODUCT_NAME)
    file_path = download_jdbc_driver(database_params[0])
    deploy_jdbc_driver(provider, server, file_path, driver_name=database_params[1],
                       module_name=database_params[2], driver_class=database_params[3],
                       major_version=database_params[4], minor_version=database_params[5])
