from urlparse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils import conf


def pytest_sessionstart(session):
    """Setup run for tests"""
    import db
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
    db.engine = create_engine(db.cfme_db_url)


@pytest.fixture
def db_session():
    """Creates a database session based on the db url passed on the CLI

    This is an SQLalchemy (http://www.sqlalchemy.org/) session. You can make
    queries and create new rows in the database with this session.

    The available classes are dynamically generated from the database. Consult
    db/__init__.py for a list of available class -> table mappings.

    Usage:

        # This example gets vm names and hostnames from the ext_management_systems table.
        @pytest.mark.nondestructive
        def test_that_tries_for_db(db_session):
            import db
            session = db_session
            for instance in session.query(db.ExtManagementSystem).order_by(
                db.ExtManagementSystem.id):
            assert instance.name, instance.hostname

    """
    import db
    Session = sessionmaker(bind=db.engine)
    return Session()


@pytest.fixture
def db_yamls(db_session):
    """Returns the yamls from the db configuration table as a dict"""

    import db
    import yaml
    configs = db_session.query(db.Configuration.typ, db.Configuration.settings)
    data = {name: yaml.load(settings) for name, settings in configs}

    return data
