from collections import Mapping
from contextlib import contextmanager
from itertools import izip

from cached_property import cached_property
from sqlalchemy import MetaData, create_engine, event, inspect
from sqlalchemy.exc import ArgumentError, DisconnectionError, InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool

from fixtures.pytest_store import store
from utils import conf, ports, version
from utils.log import logger


@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    """ping_connection event hook, used to reconnect db sessions that time out

    Note:

        See also: :ref:`Connection Invalidation <sqlalchemy:pool_connection_invalidation>`

    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except StandardError:
        raise DisconnectionError
    cursor.close()


def scl_name():
    # postgres's version is in the service name and file paths when we pull it from SCL,
    # so this is a little resolver to help keep the version picking centralized
    return version.pick({
        version.LOWEST: 'postgresql92',
        '5.5': 'rh-postgresql94',
        '5.7': 'rh-postgresql95'
    })


class Db(Mapping):
    """Helper class for interacting with a CFME database using SQLAlchemy

    Args:
        hostname: base url to be used (default is from current_appliance)
        credentials: name of credentials to use from :py:attr:`utils.conf.credentials`
            (default ``database``)

    Provides convient attributes to common sqlalchemy objects related to this DB,
    as well as a Mapping interface to access and reflect database tables. Where possible,
    attributes are cached.

    Db objects support getting tables by name via the mapping interface::

        table = db['table_name']

    Usage:

        # Usually used to query the DB for info, here's a common query
        for vm in db.session.query(db['vms']).all():
            print(vm.name)
            print(vm.guid)

        # List comprehension to get all templates
        [(vm.name, vm.guid) for vm in session.query(db['vms']).all() if vm.template is True]

        # Use the transaction manager for write operations:
        with db.transaction:
            db.session.query(db['vms']).all().delete()

    Note:

        Creating a table object requires a call to the database so that SQLAlchemy can do
        reflection to determine the table's structure (columns, keys, indices, etc). On
        a latent connection, this can be extremely slow, which will affect methods that return
        tables, like the mapping interface or :py:meth:`values`.

    """
    def __init__(self, hostname=None, credentials=None):
        self._table_cache = {}
        if hostname is None:
            self.hostname = store.current_appliance.db_address
        else:
            self.hostname = hostname

        self.credentials = credentials or conf.credentials['database']

    def __getitem__(self, table_name):
        """Access tables as items contained in this db

        Usage:

            # To get a table called 'table_name':
            db['table_name']

        This may return ``None`` in the case where a table is found but reflection fails.

        """
        try:
            return self._table(table_name)
        except InvalidRequestError:
            raise KeyError('Table {} could not be found'.format(table_name))

    def __iter__(self):
        """Iterator of table names in this db"""
        return self.keys()

    def __len__(self):
        """Number of tables in this db"""
        return len(self.table_names)

    def __contains__(self, table_name):
        """Whether or not the named table is in this db"""
        return table_name in self.table_names

    def keys(self):
        """Iterator of table names in this db"""
        return (table_name for table_name in self.table_names)

    def items(self):
        """Iterator of ``(table_name, table)`` pairs"""
        return izip(self.keys(), self.values())

    def values(self):
        """Iterator of tables in this db"""
        return (self[table_name] for table_name in self.table_names)

    def get(self, table_name, default=None):
        """table getter

        Args:
            table_name: Name of the table to get
            default: Default value to return if ``table_name`` is not found.

        Returns: a table if ``table_name`` exists, otherwise 'None' or the passed-in default

        """
        try:
            return self[table_name]
        except KeyError:
            return default

    def copy(self):
        """Copy this database instance, keeping the same credentials and hostname"""
        return type(self)(self.hostname, self.credentials)

    def __eq__(self, other):
        """Check if this db is equal to another db"""
        try:
            return self.hostname == other.hostname
        except:
            return False

    def __ne__(self, other):
        """Check if this db is not equal to another db"""
        return not self == other

    @cached_property
    def engine(self):
        """The :py:class:`Engine <sqlalchemy:sqlalchemy.engine.Engine>` for this database

        It uses pessimistic disconnection handling, checking that the database is still
        connected before executing commands.

        """
        return create_engine(self.db_url, echo_pool=True)

    @cached_property
    def sessionmaker(self):
        """A :py:class:`sessionmaker <sqlalchemy:sqlalchemy.orm.session.sessionmaker>`

        Used to make new sessions with this database, as needed.

        """
        return sessionmaker(bind=self.engine)

    @cached_property
    def table_base(self):
        """Base class for all tables returned by this database

        This base class is created using
        :py:class:`declarative_base <sqlalchemy:sqlalchemy.ext.declarative.declarative_base>`.
        """
        return declarative_base(metadata=self.metadata)

    @cached_property
    def metadata(self):
        """:py:class:`MetaData <sqlalchemy:sqlalchemy.schema.MetaData>` for this database

        This can be used for introspection of reflected items.

        Note:

            Tables that haven't been reflected won't show up in metadata. To reflect a table,
            use :py:meth:`reflect_table`.

        """
        return MetaData(bind=self.engine)

    @cached_property
    def db_url(self):
        """The connection URL for this database, including credentials"""
        template = "postgresql://{username}:{password}@{host}:{port}/vmdb_production"
        result = template.format(host=self.hostname, port=ports.DB, **self.credentials)
        logger.info("[DB] db_url is %s", result)
        return result

    @cached_property
    def table_names(self):
        """A sorted list of table names available in this database."""
        # rails table names follow similar rules as pep8 identifiers; expose them as such
        return sorted(inspect(self.engine).get_table_names())

    @cached_property
    def session(self):
        """Returns a :py:class:`Session <sqlalchemy:sqlalchemy.orm.session.Session>`

        This is used for database queries. For writing to the database, start a
        :py:meth:`transaction`.

        Note:

            This attribute is cached. In cases where a new session needs to be explicitly created,
            use :py:meth:`sessionmaker`.

        """
        return self.sessionmaker(autocommit=True)

    @property
    @contextmanager
    def transaction(self):
        """Context manager for simple transaction management

        Sessions understand the concept of transactions, and provider context managers to
        handle conditionally committing or rolling back transactions as needed.

        Note:

            Sessions automatically commit transactions by default. For predictable results when
            writing to the database, use the transaction manager.

        Usage:

            with db.transaction:
                db.session.do_something()

        """
        with self.session.begin():
            yield

    def reflect_table(self, table_name):
        """Populate :py:attr:`metadata` with information on a table

        Args:
            table_name: The name of a table to reflect

        """
        self.metadata.reflect(only=[table_name])

    def _table(self, table_name):
        """Retrieves, reflects, and caches table objects

        Actual implementation of __getitem__
        """
        try:
            return self._table_cache[table_name]
        except KeyError:
            self.reflect_table(table_name)
            table = self.metadata.tables[table_name]
            table_dict = {
                '__table__': table,
                '__tablename__': table_name
            }

            try:
                table_cls = type(str(table_name), (self.table_base,), table_dict)
                self._table_cache[table_name] = table_cls
                return table_cls
            except ArgumentError:
                # This usually happens on join tables with no PKs
                logger.info('Unable to create table class for table "{}"'.format(table_name))
                return None


@contextmanager
def database_on_server(hostname, **kwargs):
    db_obj = Db(hostname=hostname, **kwargs)
    yield db_obj


#: :py:class:`Db` instance configured with default settings from conf yamls
def cfmedb():
    return store.current_appliance.db
