# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider

pytestmark = [
    pytest.mark.appliance(['regular-app', 'multi-region-app'], scope='function'),
    pytest.mark.provider([InfraProvider], scope='module'),
    test_requirements.multi_region,
]


def test_my_lovely_test(env, appliance, provider):
    print(appliance)
    print(provider)
    pass
