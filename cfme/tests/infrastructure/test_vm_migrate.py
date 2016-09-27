# -*- coding: utf-8 -*-
import pytest

from cfme.common.vm import VM
from cfme.services import requests
from cfme.web_ui import flash
from cfme import test_requirements

from utils.wait import wait_for
from utils import testgen

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    test_requirements.vm_migrate,
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter'])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


@pytest.mark.tier(2)
@pytest.mark.meta(blockers=[1256903])
def test_vm_migrate(setup_provider, provider, request):
    """Tests migration of a vm

    Metadata:
        test_flag: migrate, provision
    """
    # auto_test_services should exist to test migrate VM
    vm = VM.factory("auto_test_services", provider)
    vm.migrate_vm("email@xyz.com", "first", "last")
    flash.assert_no_errors()
    row_description = 'auto_test_services'
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=600, delay=20)
    assert row.request_state.text == 'Migrated'
