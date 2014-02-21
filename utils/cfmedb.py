from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from urlparse import urlparse

import db
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import conf
from utils.datafile import load_data_file
from utils.path import data_path
from utils.ssh import SSHClient


def build_cfme_db_url(base_url=None, credentials=None):
    """Builds cfme db url from base url and credentials (both optional)

    Args:
        base_url: base url to be used (default ``conf.env['base_url']``)
        credentials: credentials to be used (default ``conf.credentials['database']``)

    """
    credentials = credentials or conf.credentials['database']
    base_url = base_url or conf.env['base_url']
    subs = {
        'host': urlparse(base_url).hostname
    }
    subs.update(credentials)
    template = "postgres://{username}:{password}@{host}:5432/vmdb_production"
    return template.format(**subs)


@contextmanager
def db_session(cfme_db_url=None):
    """A db session context manager to be used for custom, separate db session

    Args:
        cfme_db_url: cfme_db_url used for the session (default ``None``)

    Usage:
        cfme_db_url = cfmedb.build_cfme_db_url('1.2.3.4')
        with cfmedb.db_session(cfme_db_url) as db:
            # do stuff with seperate db session
        # Db session will be reset to the original state here

    Note:

        If cfme_db_url is set to ``None``, :py:func:``db_session_maker`` will
        take over and choose/build appropriate cfme_db_url to use.

    """
    original_cfme_db_url = db.cfme_db_url
    db.cfme_db_url = cfme_db_url

    yield db_session_maker(recreate=True)

    db.cfme_db_url = original_cfme_db_url
    db_session_maker(recreate=True)


def db_session_maker(recreate=False):
    """Create an SQLalchemy database session

    Args:
        recreate: If ``True``, force recreation of a new session (default ``False``)

    Note:

        SQLalchemy DB connection URL can be explicitly configured in env.yaml, with
        the ``cfme_db_url`` key. Additionally, ``db.cfme_db_url`` can be rebound at
        runtime, and sessions can be generated with that new URL by settings the
        ``recreate`` argument to ``True``.

    """
    if db.sessionmaker is None or recreate:
        if db.cfme_db_url is None:
            try:
                db.cfme_db_url = conf.env['cfme_db_url']
            except KeyError:
                # figure it out
                db.cfme_db_url = build_cfme_db_url()
        # Cache the engine and sessionmaker on the db "module"
        db.engine = create_engine(db.cfme_db_url)
        db.sessionmaker = sessionmaker(bind=db.engine)
    return db.sessionmaker()


def db_yamls(db_session=None):
    """Returns the yamls from the db configuration table as a dict

    Usage:

        # Get all the yaml configs
        configs = db_yamls

        # Get all the yaml names
        configs.keys()

        # Retrieve a specific yaml (but you should use get_yaml_config here)
        vmdb_config = configs['vmdb']

    """
    db_session = db_session or db_session_maker()
    configs = db_session.query(db.Configuration.typ, db.Configuration.settings)
    data = {name: yaml.load(settings) for name, settings in configs}

    return data


def get_yaml_config(config_name, db_session=None):
    """Return a specific yaml from the db configuration table as a dict

    Usage:

        # Retrieve a specific yaml
        vmdb_config = get_yaml_config('vmdb')

    """
    return db_yamls(db_session)[config_name]


def set_yaml_config(config_name, data_dict, hostname=None):
    """Given a yaml name, dictionary and hostname, set the configuration yaml on the server

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
        _ssh_client = SSHClient()
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
