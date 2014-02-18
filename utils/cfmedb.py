from tempfile import NamedTemporaryFile
from urlparse import urlparse

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import conf
from utils.datafile import load_data_file
from utils.path import data_path
from fixtures.ssh_client import ssh_client


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
    import db
    if db.sessionmaker is None or recreate:
        if db.cfme_db_url is None:
            try:
                db.cfme_db_url = conf.env['cfme_db_url']
            except KeyError:
                # figure it out
                credentials = conf.credentials['database']
                base_url = conf.env['base_url']
                subs = {
                    'host': urlparse(base_url).hostname
                }
                subs.update(credentials)
                template = "postgres://{username}:{password}@{host}:5432/vmdb_production"
                db.cfme_db_url = template.format(**subs)
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
    import db
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


def set_yaml_config(config_name, data_dict):
    """Given a yaml name and dictionary, set the configuration yaml on the server

    Warning:

        Manually editing the config yamls is potentially dangerous. Furthermore,
        the rails runner doesn't return useful information on the outcome of the
        set request, so errors that arise from the newly loading config file
        will go unreported.

    Usage:

        # Update the appliance name, for example
        vmbd_yaml = get_yaml_config('vmdb')
        vmdb_yaml['server']['name'] = 'EVM IS AWESOME'
        set_yaml_config('vmdb', vmdb_yaml)

    """
    # CFME does a lot of things when loading a configfile, so
    # let their native conf loader handle the job
    _ssh_client = ssh_client()
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
