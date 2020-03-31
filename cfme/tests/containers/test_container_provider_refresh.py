from copy import deepcopy

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.session import make_transient

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.containers,
    pytest.mark.provider(
        [ContainersProvider],
        scope='function',
        selector=ONE_PER_VERSION),
]


@pytest.fixture(scope='function')
def setup_temp_appliance_provider(temp_appliance_preconfig, provider):
    # Workaround for setting up a provider on a temp appliance
    with temp_appliance_preconfig:
        provider.create()
        # Wait for refresh so the DB is populated
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
        yield provider
        provider.delete()


@pytest.mark.customer_scenario
@pytest.mark.meta(automates=[1749060, 1732442])
def test_dup_db_entry_refresh(setup_temp_appliance_provider, temp_appliance_preconfig, provider):

    """
    Polarion:
        assignee: juwatts
        caseimportance: critical
        casecomponent: Containers
        initialEstimate: 1/6h

    Bugzilla:
        1732442
        1749060
    """
    appliance = temp_appliance_preconfig

    image_table = appliance.db.client['container_groups']

    image_query = appliance.db.client.session.query(image_table)

    all_db_entries = image_query.all()

    if not all_db_entries:
        pytest.fail("No Entries in the containter_groups DB table")

    # Grab the first entry in the table
    db_entry = all_db_entries[0]

    copied_db_entry = deepcopy(db_entry)

    # Remove the object from the session
    appliance.db.client.session.expunge(db_entry)

    make_transient(db_entry)

    # ID is the primary key, set it to something high
    db_entry_last = all_db_entries[-1]
    copied_db_entry.id = db_entry_last.id + 500

    try:
        with appliance.db.client.transaction:
            appliance.db.client.session.add(copied_db_entry)
    except IntegrityError as ex:
        pytest.fail(
            f'Exception while adding DB entry. {ex}'
        )

    new_db_entry = image_query.filter(image_table.id == copied_db_entry.id).all()

    # Should only be one entry
    assert len(new_db_entry) == 1

    for column, value in vars(new_db_entry[0]).items():
        # _sa_instance_state is an sqlalchemy InstanceState key object
        if column == "_sa_instance_state":
            continue
        elif column == "id":
            assert value != getattr(db_entry, column)
        else:
            # Verify the entries in the DB are the same
            assert value == getattr(db_entry, column)

    with LogValidator('/var/www/miq/vmdb/log/evm.log',
                      failure_patterns=['.*nil:NilClass.*'],
                      ).waiting(timeout=600):
        provider.refresh_provider_relationships()
        wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)
