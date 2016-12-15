import os
import pytest
from contextlib import closing
from urllib2 import urlopen, HTTPError
from cfme.exceptions import JDBCDriverConfigNotFound
from utils import conf
from deployment_methods import get_resource_path


class JDBCDriver():
    """
    Class which contains properties to be used during JDBC driver creation,
    each property is an array with necessary fields used during creation.

    Args:
        database_name is used for JDBC Driver download from url.
        driver_name name of driver.
        module_name the module name.
        driver_class jdbc driver class.
        major_version major version of driver.
        minor_version minor version of driver.
    """
    def __init__(self, database_name, driver_name, module_name, driver_class,
                 major_version=None, minor_version=None):
        self.database_name = database_name
        self.driver_name = driver_name
        self.module_name = module_name
        self.driver_class = driver_class
        self.major_version = major_version
        self.minor_version = minor_version


DB2_105_JDBC = JDBCDriver('db2-105', 'db2', 'com.ibm', 'com.ibm.db2.jcc.DB2Driver', '', '')
MSSQL_2014_JDBC = JDBCDriver('mssql2014', 'mssql', 'com.microsoft',
              'com.microsoft.sqlserver.jdbc.SQLServerDriver', '', '')
MYSQL_57_JDBC = JDBCDriver('mysql57', 'mysql', 'com.mysql', 'com.mysql.jdbc.Driver', '5', '1')
POSTGRESPLUS_94_JDBC = JDBCDriver('postgresplus94', 'edb', 'com.edb', 'com.edb.Driver', '', '')
POSTGRESQL_94_JDBC = JDBCDriver('postgresql94', 'postgresql', 'org.postgresql',
                      'org.postgresql.Driver', '', '')
SYBASE_157_JDBC = JDBCDriver('sybase157', 'sybase', 'com.sybase',
                   'com.sybase.jdbc4.jdbc.SybDriver', '', '')
ORACLE_12C_JDBC = JDBCDriver('oracle12c', 'oracle12c', 'com.oracle.jdbc',
                             'oracle.jdbc.OracleDriver', '', '')
MARIADB10_JDBC = JDBCDriver('mariadb10', 'mariadb10', 'org.mariadb',
                            'org.mariadb.jdbc.Driver', '', '')


def download_jdbc_driver(database_name):
    """Downloads JDBC Driver from 'jdbc_drivers_url' by given database name.
    Returns the path of downloaded file.
    """
    try:
        jdbc_drivers_url = conf.cfme_data.get(
            'resources', {})['databases']['jdbc_drivers']['jdbc_drivers_url']
        with closing(urlopen(jdbc_drivers_url.format(database_name, 'meta-inf.txt'))) as http:
            driver_name = http.read().strip()
            driver_path = get_resource_path(driver_name)
            if os.path.exists(driver_path):
                return driver_path
        with closing(urlopen(jdbc_drivers_url.format(database_name, driver_name))) as http:
            data = http.read()
            with open(driver_path, "wb") as file_path:
                file_path.write(data)
            return driver_path
    except KeyError:
        raise JDBCDriverConfigNotFound(
            "jdbc_drivers_url configuration is missing in cfme_data.yaml")
    except HTTPError as e:
        pytest.fail('Error {} while allocating database {}'.format(e, database_name))


def deploy_jdbc_driver(provider, server, file_path, driver_name, module_name,
                       driver_class, major_version=None, minor_version=None):
    """Deploys JDBC driver file into provided server.
    Refreshes the provider relationships via REST call.
    """
    server.add_jdbc_driver(file_path, driver_name, module_name, driver_class,
                           major_version, minor_version)
    provider.refresh_provider_relationships()
