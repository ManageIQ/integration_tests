# -*- coding: utf-8 -*-
import datetime
import pytest

from cfme import test_requirements
from cfme.rest.gen_data import a_provider as _a_provider
from cfme.rest.gen_data import vm as _vm
from utils.wait import wait_for


pytestmark = [test_requirements.retirement]


@pytest.fixture(scope="function")
def a_provider():
    return _a_provider()


@pytest.fixture(scope="function")
def vm(request, a_provider, rest_api):
    return _vm(request, a_provider, rest_api)


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "from_collection", [True, False],
    ids=["from_collection", "from_detail"])
def test_retire_vm_now(rest_api, vm, from_collection):
    """Test retirement of vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``retire``)
        OR
        * POST /api/vms (method ``retire``) with ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    retire_vm = rest_api.collections.vms.get(name=vm)
    if from_collection:
        rest_api.collections.vms.action.retire(retire_vm)
    else:
        retire_vm.action.retire()
    assert rest_api.response.status_code == 200

    def _finished():
        retire_vm.reload()
        # The retirement_state field appears after calling retire method
        try:
            if retire_vm.retirement_state == "retired":
                return True
        except AttributeError:
            pass
        return False

    wait_for(_finished, num_sec=1500, delay=10, message="REST vm retire now")


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "from_collection", [True, False],
    ids=["from_collection", "from_detail"])
def test_retire_vm_future(rest_api, vm, from_collection):
    """Test retirement of vm

    Prerequisities:

        * An appliance with ``/api`` available.
        * VM

    Steps:

        * POST /api/vms/<id> (method ``retire``) with the ``retire_date``
        OR
        * POST /api/vms (method ``retire``) with the ``retire_date`` and ``href`` of the vm or vms

    Metadata:
        test_flag: rest
    """
    retire_vm = rest_api.collections.vms.get(name=vm)
    date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%m/%d/%Y")
    future = {
        "date": date,
        "warn": "4",
    }
    date_before = retire_vm.updated_on
    if from_collection:
        future.update(retire_vm._ref_repr())
        rest_api.collections.vms.action.retire(future)
    else:
        retire_vm.action.retire(future)
    assert rest_api.response.status_code == 200

    def _finished():
        retire_vm.reload()
        try:
            if retire_vm.updated_on > date_before and retire_vm.retires_on:
                return True
        except AttributeError:
            pass
        return False

    wait_for(_finished, num_sec=1500, delay=10, message="REST vm retire future")
