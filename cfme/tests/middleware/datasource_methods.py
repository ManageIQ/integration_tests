import fauxfactory
from utils.wait import wait_for
from jdbc_driver_methods import DB2_105_JDBC, MSSQL_2014_JDBC, MYSQL_57_JDBC
from jdbc_driver_methods import POSTGRESPLUS_94_JDBC, POSTGRESQL_94_JDBC
from jdbc_driver_methods import SYBASE_157_JDBC, ORACLE_12C_JDBC, MARIADB10_JDBC
from cfme.middleware.datasource import MiddlewareDatasource
from dballocator_methods import (
    MSSQL_2014_DBALLO, DB2_105_DBALLO, POSTGRESPLUS_94_DBALLO,
    MYSQL_57_DBALLO, POSTGRESQL_94_DBALLO, SYBASE_157_DBALLO,
    ORACLE_12C_DBALLO, ORACLE_12C_RAC_DBALLO, MARIADB_10_DBALLO
)
from server_methods import refresh


class Datasource():
    """
    Class which contains properties to be used during Datasource creation,
    each property is an array with necessary fields used during creation.

    Args:
        database_type Database Type used in creation form.
        datasource_name name of datasource.
        jndi_name JNDI name of datasource.
        connection_urlDatabase connection URL.
        username Database username.
        password Database password.
        dballocator_name Database name in DBAllocator.
        driver Structure of properties of JDBC Driver creation, from jdbc_driver_methods.py.
    """
    def __init__(self, database_type, datasource_name, jndi_name, connection_url,
                 username, password, dballocator_name=None, driver=None):
        self.database_type = database_type
        self.datasource_name = '{}{}'.format(datasource_name, fauxfactory.gen_alphanumeric(4))
        self.jndi_name = '{}{}'.format(jndi_name, fauxfactory.gen_alphanumeric(4))
        self.connection_url = connection_url
        self.username = username
        self.password = password
        self.dballocator_name = dballocator_name
        self.driver = driver


H2_DS = Datasource('H2', 'H2DS', 'java:/H2DS',
      'jdbc:h2:mem:test;DB_CLOSE_DELAY=-1', 'admin', '')
DB2_105_DS = Datasource('IBM DB2', 'DB2DS', 'java:/DB2DS',
           'jdbc:ibmdb2://db2', 'admin', '',
           DB2_105_DBALLO, DB2_105_JDBC)
MSSQL_2014_DS = Datasource('Microsoft SQL Server', 'MSSQLDS', 'java:/MSSQLDS',
              'jdbc:sqlserver://localhost:1433;DatabaseName=MyDatabase', 'admin', '',
              MSSQL_2014_DBALLO, MSSQL_2014_JDBC)
MYSQL_57_DS = Datasource('MySql', 'MySqlDS', 'java:/MySqlDS',
            'jdbc:mysql://localhost:3306/mysqldb', 'admin', '',
            MYSQL_57_DBALLO, MYSQL_57_JDBC)
POSTGRESPLUS_94_DS = Datasource('Postgres', 'PostgresPlusDS', 'java:/PostgresPlusDS',
                   'jdbc:postresql://localhost:5432/postgresdb', 'admin', '',
                   POSTGRESPLUS_94_DBALLO, POSTGRESPLUS_94_JDBC)
POSTGRESQL_94_DS = Datasource('Postgres', 'PostgresDS', 'java:/PostgresDS',
                 'jdbc:postresql://localhost:5432/postgresdb', 'admin', '',
                 POSTGRESQL_94_DBALLO, POSTGRESQL_94_JDBC)
SYBASE_157_DS = Datasource('Sybase', 'SybaseDS', 'java:/SybaseDB',
              'jdbc:sybase:Tds:localhost:5000/mydatabase?JCONNECT_VERSION=6', 'admin', '',
              SYBASE_157_DBALLO, SYBASE_157_JDBC)
ORACLE_12C_DS = Datasource('Oracle', 'OracleDS', 'java:/OracleDS',
              'jdbc:oracle:thin:@localhost:1521:orcalesid', 'admin', '',
              ORACLE_12C_DBALLO, ORACLE_12C_JDBC)
ORACLE_12C_RAC_DS = Datasource('Oracle', 'OracleRACDS', 'java:/OracleRACDS',
                  'jdbc:oracle:thin:@(DESCRIPTION=(LOAD_BALANCE=on)(ADDRESS=(PROTOCOL=TCP)' +
                  '(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=qaora)))', 'admin', '',
                  ORACLE_12C_RAC_DBALLO, ORACLE_12C_JDBC)
MARIADB10_DS = Datasource('MariaDB', 'MariaDBDS', 'java:/MariaDBDS',
             'jdbc:mariadb://localhost:3306/mariadb', 'admin', '',
             MARIADB_10_DBALLO, MARIADB10_JDBC)


def get_datasources_set(datasources):
    """
    Return the set of datasources which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((datasource.name, datasource.server.name) for datasource in datasources)


def get_datasources_name(datasources):
    """
    Return the set of datasources names
    """
    return set((datasource.name) for datasource in datasources)


def generate_ds_name(ds_name):
    return "{}{}".format(ds_name, fauxfactory.gen_alpha(8).lower())


def verify_datasource_listed(provider, name, server=None):
    refresh(provider)
    wait_for(lambda: name in
        get_datasources_name(
            MiddlewareDatasource.datasources(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Datasource {} must be found'
        .format(name),
        fail_func=lambda: refresh(provider))


def verify_datasource_not_listed(provider, name, server=None):
    refresh(provider)
    wait_for(lambda: name not in
        get_datasources_name(
            MiddlewareDatasource.datasources(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Datasource {} must not be found'
        .format(name),
        fail_func=lambda: refresh(provider))


def get_datasource_from_list(provider, name, server=None):
    verify_datasource_listed(provider, name, server)
    for datasource in MiddlewareDatasource.datasources(provider=provider, server=server):
        if datasource.name == name:
            return datasource
    raise ValueError('Recently created datasource {} was not found in datasource list'
                     .format(name))
