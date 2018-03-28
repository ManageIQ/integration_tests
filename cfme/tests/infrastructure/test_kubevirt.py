# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.infrastructure.provider.kubevirt import KubeVirtProvider
from cfme.utils.update import update


pytestmark = [
    pytest.mark.provider([KubeVirtProvider], scope="module")
]


def test_cnv_provider_crud(provider):
    provider.create()

    with update(provider):
        provider.name = fauxfactory.gen_alphanumeric() + '_updated'

    provider.delete(cancel=False)
    provider.wait_for_delete()
