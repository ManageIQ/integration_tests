# -*- coding: utf-8 -*-
import datetime

import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import vm as _vm
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.retirement,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope="function")
def vm(request, provider, appliance):
    return _vm(request, provider, appliance)


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "from_collection", [True, False],
    ids=["from_collection", "from_detail"])
def test_retire_vm_now(appliance, vm, from_collection):
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

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/3h
    """
    retire_vm = appliance.rest_api.collections.vms.get(name=vm)
    if from_collection:
        appliance.rest_api.collections.vms.action.retire(retire_vm)
    else:
        retire_vm.action.retire()
    assert_response(appliance)

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
def test_retire_vm_future(appliance, vm, from_collection):
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

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/3h
    """
    retire_vm = appliance.rest_api.collections.vms.get(name=vm)
    date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y/%m/%d")
    future = {
        "date": date,
        "warn": "4",
    }
    if from_collection:
        future.update(retire_vm._ref_repr())
        appliance.rest_api.collections.vms.action.retire(future)
    else:
        retire_vm.action.retire(**future)
    assert_response(appliance)

    def _finished():
        retire_vm.reload()
        if not hasattr(retire_vm, "retires_on"):
            return False
        if not hasattr(retire_vm, "retirement_warn"):
            return False
        return True

    wait_for(_finished, num_sec=1500, delay=10, message="REST vm retire future")
