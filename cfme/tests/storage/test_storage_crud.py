# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.storage.managers import StorageManager
from utils.update import update
from utils.version import current_version

pytestmark = [pytest.mark.usefixtures("use_storage")]


@pytest.mark.uncollectif(lambda: not current_version().is_in_series("5.2"))
def test_storage_manager_crud(request):
    sm = StorageManager(
        name=fauxfactory.gen_alphanumeric(),
        type=StorageManager.NETAPP_RS,
        hostname=fauxfactory.gen_alphanumeric(),
        ip="127.0.0.250",
        port="12345",
        credentials=StorageManager.Credential(
            username="test",
            password="pw"
        )

    )
    request.addfinalizer(lambda: sm.delete() if sm.exists else None)
    assert not sm.exists
    sm.create(validate=False)
    assert sm.exists
    with update(sm, validate=False):
        sm.hostname = fauxfactory.gen_alphanumeric()
    assert sm.exists
    sm.delete()
    assert not sm.exists
