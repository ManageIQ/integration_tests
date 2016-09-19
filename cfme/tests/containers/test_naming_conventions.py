# -*- coding: UTF-8 -*-

import uuid

import pytest

from utils.providers import setup_a_provider
from utils.update import update


@pytest.yield_fixture(scope="function")
def a_container_provider():
    prov = setup_a_provider("container", create=False)
    yield prov
    prov.delete_if_exists(cancel=False)
    prov.wait_for_delete()


# CMP - 9836
@pytest.mark.usefixtures('has_no_container_providers')
@pytest.mark.usefixtures('a_container_provider')
@pytest.mark.tier(2)
def test_provider_unicode_name(a_container_provider):
    """Tests provider addition with good credentials and unicode in the name.
       Tests updating it with another unicode name.
    """
    provider = a_container_provider
    assert not provider.exists

    old_name = provider.name
    provider.name = "Unicode name 1 «ταБЬℓσ» {}".format(uuid.uuid4())
    provider.create()
    provider.validate()

    with update(provider):
        provider.name = "Unicode name 2 «ταБЬℓσ» {}".format(uuid.uuid4())

    with update(provider):
        provider.name = old_name  # old name
