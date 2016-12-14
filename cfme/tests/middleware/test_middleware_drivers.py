import pytest
from cfme.middleware.provider.hawkular import HawkularProvider
from utils import testgen
from utils.version import current_version
from server_methods import get_eap_server
from jdbc_driver_methods import download_jdbc_driver, deploy_jdbc_driver
from jdbc_driver_methods import ORACLE_12C_JDBC, DB2_105_JDBC, MSSQL_2014_JDBC, MYSQL_57_JDBC
from jdbc_driver_methods import POSTGRESPLUS_94_JDBC, POSTGRESQL_94_JDBC, SYBASE_157_JDBC

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")
ITEMS_LIMIT = 5  # when we have big list, limit number of items to test

DRIVERS = [ORACLE_12C_JDBC,
           DB2_105_JDBC,
           MSSQL_2014_JDBC,
           MYSQL_57_JDBC,
           POSTGRESPLUS_94_JDBC,
           POSTGRESQL_94_JDBC,
           SYBASE_157_JDBC]


@pytest.mark.parametrize("driver", DRIVERS)
def test_deploy_driver(provider, driver):
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
    server = get_eap_server(provider)
    file_path = download_jdbc_driver(driver.database_name)
    deploy_jdbc_driver(provider, server, file_path,
                       driver_name=driver.driver_name,
                       module_name=driver.module_name,
                       driver_class=driver.driver_class,
                       major_version=driver.major_version,
                       minor_version=driver.minor_version)
