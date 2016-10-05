import os
import pytest
from contextlib import closing
from urllib2 import urlopen, HTTPError
from cfme.exceptions import JDBCDriverConfigNotFound
from utils import conf
from deployment_methods import get_resource_path


"""Properties to be used during JDBC driver creation,
each property is an array with necessary fields used during creation.
PROPERTIES[0] is used for JDBC Driver download from url.
PROPERTIES[1] name of driver.
PROPERTIES[2] module name.
PROPERTIES[3] jdbc driver class.
PROPERTIES[4] major version of driver.
PROPERTIES[5] minor version of driver.
"""
DB2_105_JDBC = ['db2-105', 'db2', 'com.ibm', 'com.ibm.db2.jcc.DB2Driver', '', '']
MSSQL_2014_JDBC = ['mssql2014', 'mssql', 'com.microsoft',
              'com.microsoft.sqlserver.jdbc.SQLServerDriver', '', '']
MYSQL_57_JDBC = ['mysql57', 'mysql', 'com.mysql', 'com.mysql.jdbc.Driver', '5', '1']
POSTGRESPLUS_94_JDBC = ['postgresplus94', 'edb', 'com.edb', 'com.edb.Driver', '', '']
POSTGRESQL_94_JDBC = ['postgresql94', 'postgresql', 'org.postgresql',
                      'org.postgresql.Driver', '', '']
SYBASE_157_JDBC = ['sybase157', 'sybase', 'com.sybase',
                   'com.sybase.jdbc4.jdbc.SybDriver', '', '']
ORACLE_12C_JDBC = ['oracle12c', 'oracle12c', 'com.oracle', 'oracle.jdbc.OracleDriver', '', '']
MARIADB10_JDBC = ['mariadb10', 'mariadb10', 'org.mariadb', 'org.mariadb.jdbc.Driver', '', '']


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
