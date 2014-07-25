# -*- coding: utf-8 -*-
import pytest

from cfme.storage.managers import StorageManager
from utils.randomness import generate_random_string
from utils.update import update

pytestmark = [pytest.mark.usefixtures("use_storage")]


def test_storage_manager_crud(request):
    sm = StorageManager(
        name=generate_random_string(),
        type=StorageManager.NETAPP_RS,
        hostname=generate_random_string(),
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
        sm.hostname = generate_random_string()
    assert sm.exists
    sm.delete()
    assert not sm.exists
