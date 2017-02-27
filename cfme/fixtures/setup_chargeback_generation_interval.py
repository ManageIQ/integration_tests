from datetime import datetime

import pytest


@pytest.yield_fixture(scope="module")
def setup_chargeback_generation_interval(appliance):
    """Changing the chargeback_generation_interval to enable quick production
    of chargeback report"""
    settings_changes = appliance.db['settings_changes']
    pkey = settings_changes.__table__.insert().values(
        resource_type='MiqServer', resource_id=1,
        key='/workers/worker_base/schedule_worker/chargeback_generation_interval',
        value='--- 1.minutes\n...\n',
        created_at=datetime.now(),
        updated_at=datetime.now()
    ).execute().inserted_primary_key[-1]
    yield
    settings_changes.__table__.delete().where(settings_changes.id == pkey).execute()
