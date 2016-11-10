from utils.wait import wait_for
from jdbc_driver_methods import DB2_105_JDBC, MSSQL_2014_JDBC, MYSQL_57_JDBC
from jdbc_driver_methods import POSTGRESPLUS_94_JDBC, POSTGRESQL_94_JDBC
from jdbc_driver_methods import SYBASE_157_JDBC, ORACLE_12C_JDBC, MARIADB10_JDBC
from cfme.middleware.datasource import MiddlewareDatasource
from dballocator_methods import MSSQL_2014_DBALLO, DB2_105_DBALLO, POSTGRESPLUS_94_DBALLO
from dballocator_methods import MYSQL_57_DBALLO, POSTGRESQL_94_DBALLO, SYBASE_157_DBALLO
from dballocator_methods import ORACLE_12C_DBALLO, ORACLE_12C_RAC_DBALLO, MARIADB_10_DBALLO


"""Properties to be used during Datasource creation,
each property is an array with necessary fields used during creation.
PROPERTIES[0] Database Type used in creation form.
PROPERTIES[1] name of datasource.
PROPERTIES[2] JNDI name of datasource.
PROPERTIES[3] name of driver.
PROPERTIES[4] module name.
PROPERTIES[5] jdbc driver class.
PROPERTIES[6] Database connection URL.
PROPERTIES[7] Database username.
PROPERTIES[8] Database password.
PROPERTIES[9] Database name in DBAllocator.
"""
H2_DS = ['H2', 'H2DS', 'java:/H2DS', 'h2', 'com.h2database.h2', 'org.h2.Driver',
      'jdbc:h2:mem:test;DB_CLOSE_DELAY=-1', 'admin', '']
DB2_105_DS = ['IBM DB2', 'DB2DS', 'java:/DB2DS',
           DB2_105_JDBC[1], DB2_105_JDBC[2], DB2_105_JDBC[3],
           'jdbc:ibmdb2://db2', 'admin', '',
           DB2_105_DBALLO]
MSSQL_2014_DS = ['Microsoft SQL Server', 'MSSQLDS', 'java:/MSSQLDS',
              MSSQL_2014_JDBC[1], MSSQL_2014_JDBC[2], MSSQL_2014_JDBC[3],
              'jdbc:sqlserver://localhost:1433;DatabaseName=MyDatabase', 'admin', '',
              MSSQL_2014_DBALLO]
MYSQL_57_DS = ['MySql', 'MySqlDS', 'java:/MySqlDS',
            MYSQL_57_JDBC[1], MYSQL_57_JDBC[2], MYSQL_57_JDBC[3],
            'jdbc:mysql://localhost:3306/mysqldb', 'admin', '',
            MYSQL_57_DBALLO]
POSTGRESPLUS_94_DS = ['Postgres', 'PostgresPlusDS', 'java:/PostgresPlusDS',
                   POSTGRESPLUS_94_JDBC[1], POSTGRESPLUS_94_JDBC[2], POSTGRESPLUS_94_JDBC[3],
                   'jdbc:postresql://localhost:5432/postgresdb', 'admin', '',
                   POSTGRESPLUS_94_DBALLO]
POSTGRESQL_94_DS = ['Postgres', 'PostgresDS', 'java:/PostgresDS',
                 POSTGRESQL_94_JDBC[1], POSTGRESQL_94_JDBC[2], POSTGRESQL_94_JDBC[3],
                 'jdbc:postresql://localhost:5432/postgresdb', 'admin', '',
                 POSTGRESQL_94_DBALLO]
SYBASE_157_DS = ['Sybase', 'SybaseDS', 'java:/SybaseDB',
              SYBASE_157_JDBC[1], SYBASE_157_JDBC[2], SYBASE_157_JDBC[3],
              'jdbc:sybase:Tds:localhost:5000/mydatabase?JCONNECT_VERSION=6', 'admin', '',
              SYBASE_157_DBALLO]
ORACLE_12C_DS = ['Oracle', 'OracleDS', 'java:/OracleDS',
              ORACLE_12C_JDBC[1], ORACLE_12C_JDBC[2], ORACLE_12C_JDBC[3],
              'jdbc:oracle:thin:@localhost:1521:orcalesid', 'admin', '',
              ORACLE_12C_DBALLO]
ORACLE_12C_RAC_DS = ['Oracle', 'OracleRACDS', 'java:/OracleRACDS',
                  ORACLE_12C_JDBC[1], ORACLE_12C_JDBC[2], ORACLE_12C_JDBC[3],
                  'jdbc:oracle:thin:@(DESCRIPTION=(LOAD_BALANCE=on)(ADDRESS=(PROTOCOL=TCP)' +
                  '(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=qaora)))', 'admin', '',
                  ORACLE_12C_RAC_DBALLO]
MARIADB10_DS = ['MariaDB', 'MariaDBDS', 'java:/MariaDBDS',
             MARIADB10_JDBC[1], MARIADB10_JDBC[2], MARIADB10_JDBC[3],
             'jdbc:mariadb://localhost:3306/mariadb', 'admin', '',
             MARIADB_10_DBALLO]


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


def check_datasource_listed(provider, name, server=None):
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda: name in
        get_datasources_name(
            MiddlewareDatasource.datasources(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Datasource {} must be found'
        .format(name))


def check_datasource_not_listed(provider, name, server=None):
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda: name not in
        get_datasources_name(
            MiddlewareDatasource.datasources(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Datasource {} must not be found'
        .format(name))


def get_datasource_from_list(provider, name, server=None):
    check_datasource_listed(provider, name, server)
    for datasource in MiddlewareDatasource.datasources(provider=provider, server=server):
        if datasource.name == name:
            return datasource
    raise ValueError('Recently created datasource {} was not found in datasource list'
                     .format(name))
