import pytest

from utils.cfmedb import db_session_maker


@pytest.fixture
def db_session(uses_db):
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
    return db_session_maker()


@pytest.fixture
def db_yamls(db_session=None):
    """Returns the yamls from the db configuration table as a dict"""

    import db
    import yaml
    db_session = db_session or db_session_maker()
    configs = db_session.query(db.Configuration.typ, db.Configuration.settings)
    data = {name: yaml.load(settings) for name, settings in configs}

    return data
