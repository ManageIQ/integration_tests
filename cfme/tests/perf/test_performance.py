from timeit import timeit

import pytest

from cfme import test_requirements
from cfme.base.ui import navigate_to
from cfme.services.myservice import MyService
from cfme.tests.test_db_migrate import download_and_migrate_db
from cfme.utils.conf import cfme_data


@pytest.fixture
def appliance_with_performance_db(temp_appliance_extended_db):
    app = temp_appliance_extended_db
    db_backups = cfme_data['db_backups']
    performance_db = db_backups['performance_510']
    download_and_migrate_db(app, performance_db.url, performance_db.desc)
    yield app


@test_requirements.service
def test_services_performance(appliance_with_performance_db):
    """
    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Services

    Bugzilla:
        1688937
    """

    app = appliance_with_performance_db
    assert 50000 == app.rest_api.collections.services.count

    my_service = MyService(app)
    # Timeit seems to accept callable as well as string of Python code on cPython.
    assert timeit(lambda: navigate_to(my_service, 'All'), number=1) < 60
