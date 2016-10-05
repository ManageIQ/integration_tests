import pytest
from contextlib import contextmanager
from contextlib import closing
from urllib2 import urlopen, HTTPError
from cfme.exceptions import DbAllocatorConfigNotFound
from utils import conf


REQUESTEE = "cfme_tests"
DS_UUID_PROP = 'uuid'
DS_URL_PROP = 'db.jdbc_url'
DS_USERNAME_PROP = 'db.username'
DS_PASSWORD_PROP = 'db.password'
DB2_105_DBALLO = 'db2_105'
MSSQL_2014_DBALLO = 'mssql2014'
MYSQL_57_DBALLO = 'mysql57'
POSTGRESPLUS_94_DBALLO = 'postgresplus94'
POSTGRESQL_94_DBALLO = 'postgresql94'
SYBASE_157_DBALLO = 'sybase157'
ORACLE_12C_DBALLO = 'oracle12c'
ORACLE_12C_RAC_DBALLO = 'oracle12cRAC'
MARIADB_10_DBALLO = 'mariadb10'
SEP = '='


@contextmanager
def db_allocate(db_type, expiry=1):
    """
    Method for allocating database via DBAllocator tool by providing database type,
    expiry time in minutes and the name of requestee.

    It returns the result of DBAllocator allocate action in dictionary format,
    which contains the connection properties to allocated database.
    From returned properties, very important one is 'uuid',
        which will be used for manually deallocating database.

    Args:
        db_type: type of the database which is registered in DBAllocator,
            all possible types are in this class.
        expiry: reservation duration in minutes after
            which database will be automatically deallocated (optional).

    Returns:
        database connection properties as dictionary containing information:
            db.password=password
            hibernate.connection.password=password
            hibernate41.dialect=org.hibernate.dialect.PostgresPlusDialect
            broken=false
            db.username=username
            server_geo=location
            dballoc.db_type=standard
            db.jdbc_url=formatted jdbc url to connect
            db.name=database name
            db.hostname=database hostname
            datasource.class.xa=XADataSource class
            server_uid=server uid
            hibernate33.dialect=org.hibernate.dialect{}Dialect
            server_labels=server_label
            hibernate.connection.username=username
            db.jdbc_class=JDBC Driver Class
            db.schema=schema name
            hibernate.connection.driver_class=Driver Class
            uuid=uuid of database instance in DBAllocator tool, will be used in deallocation
            db.primary_label=label
            db.port=port
            server_label_primary=server label
            hibernate.dialect=org.hibernate.dialect.{}Dialect
            hibernate.connection.url=formatted jdbc url to connect
            hibernate.connection.schema=schema name

    Usage:
        properties = db_allocate('oracle12c')
    """
    try:
        db_allocate_url = conf.cfme_data.get(
            'resources', {})['databases']['db_allocator']['db_allocate_url']
        with closing(urlopen(db_allocate_url.format(db_type, expiry, REQUESTEE))) as http:
            properties = http.read().strip()
            db_metadata = parse_properties(properties)
        yield db_metadata
        db_deallocate(db_metadata[DS_UUID_PROP])
    except KeyError:
        raise DbAllocatorConfigNotFound(
            "db_allocator configuration is missing in cfme_data.yaml")
    except HTTPError as e:
        pytest.fail('Error {} while allocating database {}'.format(e, db_type))


def db_deallocate(uuid):
    """
    Method for deallocating reserved database from DBAllocator tool by provided uuid.
    uuid parameter was returned as a property during allocation.

    Args:
        uuid=uuid of database instance in DBAllocator tool.

    Usage:
        properties = db_allocate('oracle12c')
        db_deallocate(properties['uuid'])
    """
    try:
        db_deallocate_url = conf.cfme_data.get(
            'resources', {})['databases']['db_allocator']['db_deallocate_url']
        with closing(urlopen(db_deallocate_url.format(uuid))) as http:
            http.read().strip()
    except KeyError:
        raise DbAllocatorConfigNotFound(
            "db_allocator configuration is missing in cfme_data.yaml")
    except HTTPError as e:
        # ignore error in deallocation
        print(str(e))


def parse_properties(props):
    """Parses provided properties in string format into dictionary format.
    It splits string into lines and splits each line into key and value by the first occurance."""
    properties = {}
    for line in props.splitlines():
        pair = line.split(SEP, 1)
        if len(pair) == 2:
            properties.update({pair[0]: pair[1].replace('\'', '')})
    return properties
