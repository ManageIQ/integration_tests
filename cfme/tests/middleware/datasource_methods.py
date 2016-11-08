from cfme.middleware.datasource import MiddlewareDatasource
from utils.wait import wait_for
from jdbc_driver_methods import DB2_105, MSSQL_2014, MYSQL_57
from jdbc_driver_methods import POSTGRESPLUS_94, POSTGRESQL_94
from jdbc_driver_methods import SYBASE_157, ORACLE_12C, MARIADB10


H2 = ['H2', 'H2DS', 'java:/H2DS', 'h2', 'com.h2database.h2', 'org.h2.Driver',
      'jdbc:h2:mem:test;DB_CLOSE_DELAY=-1', 'admin', '']
DB2_105 = ['IBM DB2', 'DB2DS', 'java:/DB2DS',
           DB2_105[1], DB2_105[2], DB2_105[3],
           'jdbc:ibmdb2://db2', 'admin', '']
MSSQL_2014 = ['Microsoft SQL Server', 'MSSQLDS', 'java:/MSSQLDS',
              MSSQL_2014[1], MSSQL_2014[2], MSSQL_2014[3],
           'jdbc:sqlserver://localhost:1433;DatabaseName=MyDatabase', 'admin', '']
MYSQL_57 = ['MySql', 'MySqlDS', 'java:/MySqlDS',
            MYSQL_57[1], MYSQL_57[2], MYSQL_57[3],
           'jdbc:mysql://localhost:3306/mysqldb', 'admin', '']
POSTGRESPLUS_94 = ['Postgres', 'PostgresPlusDS', 'java:/PostgresPlusDS',
                   POSTGRESPLUS_94[1], POSTGRESPLUS_94[2], POSTGRESPLUS_94[3],
           'jdbc:postresql://localhost:5432/postgresdb', 'admin', '']
POSTGRESQL_94 = ['Postgres', 'PostgresDS', 'java:/PostgresDS',
                 POSTGRESQL_94[1], POSTGRESQL_94[2], POSTGRESQL_94[3],
           'jdbc:postresql://localhost:5432/postgresdb', 'admin', '']
SYBASE_157 = ['Sybase', 'SybaseDS', 'java:/SybaseDB',
              SYBASE_157[1], SYBASE_157[2], SYBASE_157[3],
           'jdbc:sybase:Tds:localhost:5000/mydatabase?JCONNECT_VERSION=6', 'admin', '']
ORACLE_12C = ['Oracle', 'OracleDS', 'java:/OracleDS',
              ORACLE_12C[1], ORACLE_12C[2], ORACLE_12C[3],
           'jdbc:oracle:thin:@localhost:1521:orcalesid', 'admin', '']
MARIADB10 = ['MariaDB', 'MariaDBDS', 'java:/MariaDBDS',
             MARIADB10[1], MARIADB10[2], MARIADB10[3],
           'jdbc:mariadb://localhost:3306/mariadb', 'admin', '']


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
