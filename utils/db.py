from collections import Mapping
from contextlib import contextmanager
from itertools import izip
from tempfile import NamedTemporaryFile

import yaml
from sqlalchemy import MetaData, create_engine, event, inspect
from sqlalchemy.exc import ArgumentError, DisconnectionError, InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool

from fixtures.pytest_store import store
from utils import conf, lazycache, ports
from utils.datafile import load_data_file
from utils.log import logger
from utils.path import data_path
from utils.signals import fire, on_signal
from utils.ssh import SSHClient


@on_signal("server_config_changed")
def invalidate_server_config():
    del store.current_appliance.db_yamls


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


class Db(Mapping):
    """Helper class for interacting with a CFME database using SQLAlchemy

    Args:
        hostname: base url to be used (default ``conf.env['base_url']``)
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
            print vm.name, vm.guid

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
    _table_cache = dict()

    def __init__(self, hostname=None, credentials=None):
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
            raise KeyError('Table %s could not be found' % table_name)

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

    @lazycache
    def engine(self):
        """The :py:class:`Engine <sqlalchemy:sqlalchemy.engine.Engine>` for this database

        It uses pessimistic disconnection handling, checking that the database is still
        connected before executing commands.

        """
        return create_engine(self.db_url, echo_pool=True)

    @lazycache
    def sessionmaker(self):
        """A :py:class:`sessionmaker <sqlalchemy:sqlalchemy.orm.session.sessionmaker>`

        Used to make new sessions with this database, as needed.

        """
        return sessionmaker(bind=self.engine)

    @lazycache
    def table_base(self):
        """Base class for all tables returned by this database

        This base class is created using
        :py:class:`declarative_base <sqlalchemy:sqlalchemy.ext.declarative.declarative_base>`.
        """
        return declarative_base(metadata=self.metadata)

    @lazycache
    def metadata(self):
        """:py:class:`MetaData <sqlalchemy:sqlalchemy.schema.MetaData>` for this database

        This can be used for introspection of reflected items.

        Note:

            Tables that haven't been reflected won't show up in metadata. To reflect a table,
            use :py:meth:`reflect_table`.

        """
        return MetaData(bind=self.engine)

    @lazycache
    def db_url(self):
        """The connection URL for this database, including credentials"""
        template = "postgresql://{username}:{password}@{host}:{port}/vmdb_production"
        result = template.format(host=self.hostname, port=ports.DB, **self.credentials)
        logger.info("[DB] db_url is {}".format(result))
        return result

    @lazycache
    def table_names(self):
        """A sorted list of table names available in this database."""
        # rails table names follow similar rules as pep8 identifiers; expose them as such
        return sorted(inspect(self.engine).get_table_names())

    @lazycache
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
                logger.info('Unable to create table class for table "%s"')
                return None


def db_yamls(db=None, guid=None):
    """Returns the yamls from the db configuration table as a dict

    Usage:

        # Get all the yaml configs
        configs = db_yamls

        # Get all the yaml names
        configs.keys()

        # Retrieve a specific yaml (but you should use get_yaml_config here)
        vmdb_config = configs['vmdb']

    """
    db = db or cfmedb()
    guid = guid or store.current_appliance.guid

    with db.transaction:
        config = db['configurations']
        servers = db['miq_servers']

        configs = db.session.query(config.typ, config.settings)\
            .join(servers, config.miq_server_id == servers.id)\
            .filter(servers.guid == guid)
        return {name: yaml.load(settings) for name, settings in configs}


def get_yaml_config(config_name, db=None, guid=None):
    """Return a specific yaml from the db configuration table as a dict

    Usage:

        # Retrieve a specific yaml
        vmdb_config = get_yaml_config('vmdb')

    """
    return db_yamls(db, guid)[config_name]


def set_yaml_config(config_name, data_dict, hostname=None):
    """Given a yaml name, dictionary and hostname, set the configuration yaml on the server

    The configuration yamls must be inserted into the DB using the ruby console, so this function
    uses SSH, not the database. It makes sense to be included here as a counterpart to
    :py:func:`get_yaml_config`

    Args:
        config_name: Name of the yaml configuration file
        data_dict: Dictionary with data to set/change
        hostname: Hostname/address of the server that we want to set up (default ``None``)

    Note:
        If hostname is set to ``None``, the default server set up for this session will be
        used. See :py:class:``utils.ssh.SSHClient`` for details of the default setup.

    Warning:

        Manually editing the config yamls is potentially dangerous. Furthermore,
        the rails runner doesn't return useful information on the outcome of the
        set request, so errors that arise from the newly loading config file
        will go unreported.

    Usage:

        # Update the appliance name, for example
        vmbd_yaml = get_yaml_config('vmdb')
        vmdb_yaml['server']['name'] = 'EVM IS AWESOME'
        set_yaml_config('vmdb', vmdb_yaml, '1.2.3.4')

    """
    # CFME does a lot of things when loading a configfile, so
    # let their native conf loader handle the job
    # If hostname is defined, connect to the specified server
    if hostname is not None:
        _ssh_client = SSHClient(hostname=hostname)
    # Else, connect to the default one set up for this session
    else:
        _ssh_client = store.current_appliance.ssh_client()
    # Build & send new config
    temp_yaml = NamedTemporaryFile()
    dest_yaml = '/tmp/conf.yaml'
    yaml.dump(data_dict, temp_yaml, default_flow_style=False)
    _ssh_client.put_file(temp_yaml.name, dest_yaml)
    # Build and send ruby script
    dest_ruby = '/tmp/load_conf.rb'
    ruby_template = data_path.join('utils', 'cfmedb_load_config.rbt')
    ruby_replacements = {
        'config_name': config_name,
        'config_file': dest_yaml
    }
    temp_ruby = load_data_file(ruby_template.strpath, ruby_replacements)
    _ssh_client.put_file(temp_ruby.name, dest_ruby)

    # Run it
    _ssh_client.run_rails_command(dest_ruby)
    fire('server_details_changed')
    fire('server_config_changed')


@contextmanager
def database_on_server(hostname, **kwargs):
    db_obj = Db(hostname=hostname, **kwargs)
    yield db_obj


#: :py:class:`Db` instance configured with default settings from conf yamls
def cfmedb():
    return store.current_appliance.db
