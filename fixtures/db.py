import pytest

import utils.db


@pytest.fixture(scope='module')
def db(uses_db):
    """Fixture providing :py:attr:`utils.db.cfmedb`

    This is an SQLalchemy-based helper class which provides access to common database functions.

    See also:

        http://www.sqlalchemy.org/ session.

    Usage:

        # This example gets vm names and hostnames from the ext_management_systems table.
        def test_that_tries_for_db(db):
            ems_table = db['ext_management_systems']
            for instance in db.session.query(ems_table.order_by(ems_table.id):)
                assert instance.name, instance.hostname

    This fixture is module scoped to ensure predictable database access
    at the module level within tests.

    """
    return utils.db.cfmedb().copy()
