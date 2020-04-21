import datetime

import pytest
from manageiq_client.filters import Q

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import vm as _vm
from cfme.utils.blockers import BZ
from cfme.utils.rest import assert_response
from cfme.utils.version import Version
from cfme.utils.version import VersionPicker
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.rest,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures("setup_provider"),
]


@pytest.fixture
def retire_action(appliance):
    return VersionPicker({Version.lowest(): 'retire', '5.11': 'request_retire'}).pick()


@pytest.fixture(scope="function")
def vm(request, provider, appliance):
    return _vm(request, provider, appliance)


@pytest.fixture
def retire_vm(appliance, vm, provider):
    retire_vm = appliance.collections.infra_vms.instantiate(vm, provider)
    # retiring VM via UI, because retiring it via API will not generate request
    # and we will not get the retirement requester.
    retire_vm.retire()

    # using rest entity to check if the VM has retired since it is a lot faster
    _retire_vm = appliance.rest_api.collections.vms.get(name=vm)
    wait_for(
        lambda: (hasattr(_retire_vm, "retired") and _retire_vm.retired),
        timeout=1000,
        delay=5,
        fail_func=_retire_vm.reload,
    )
    return vm


@pytest.fixture
def vm_retirement_report(appliance, retire_vm):
    # Create a report for Virtual Machines that exactly matches with
    # the name of the vm that was just retired
    report_data = {
        "menu_name": "vm_retirement_requester",
        "title": "VM Retirement Requester",
        "base_report_on": "Virtual Machines",
        "report_fields": ["Name", "Retirement Requester", "Retirement State"],
        "filter": {
            "primary_filter": "fill_field(Virtual Machine : Name, =, {})".format(
                retire_vm
            )
        },
    }
    report = appliance.collections.reports.create(**report_data)
    yield retire_vm, report
    report.delete()


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "from_collection", [True, False], ids=["from_collection", "from_detail"]
)
@pytest.mark.meta(automates=[BZ(1805119)], blockers=[BZ(1805119, forced_streams=["5.10"])])
def test_retire_vm_now(appliance, vm, from_collection, retire_action):
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

    Bugzilla:
        1805119

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/3h
    """
    retire_vm = appliance.rest_api.collections.vms.get(name=vm)
    if from_collection:
        getattr(appliance.rest_api.collections.vms.action, retire_action)(retire_vm)
    else:
        getattr(retire_vm.action, retire_action)()
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
    "from_collection", [True, False], ids=["from_collection", "from_detail"]
)
@pytest.mark.meta(
    automates=[BZ(1805119), BZ(1827787)], blockers=[BZ(1827787, forced_streams=["5.10", "5.11"])]
)
def test_retire_vm_future(appliance, vm, from_collection, retire_action):
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

    Bugzilla:
        1805119
        1827787

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/3h
    """
    retire_vm = appliance.rest_api.collections.vms.get(name=vm)
    date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y/%m/%d")
    future = {"date": date, "warn": "4"}
    if from_collection:
        future.update(retire_vm._ref_repr())
        getattr(appliance.rest_api.collections.vms.action, retire_action)(future)
    else:
        getattr(retire_vm.action, retire_action)(**future)
    assert_response(appliance)

    def _finished():
        retire_vm.reload()
        if not hasattr(retire_vm, "retires_on"):
            return False
        if not hasattr(retire_vm, "retirement_warn"):
            return False
        if not hasattr(retire_vm, "retirement_state"):
            return False
        return True

    wait_for(_finished, num_sec=1500, delay=10, message="REST vm retire future")


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[BZ(1805119), BZ(1638502)])
def test_check_vm_retirement_requester(
    appliance, request, provider, vm_retirement_report
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/2h
        tags: retirement
        setup:
            1. Add a provider.
            2. Provision a VM.
            3. Once the VM has been provisioned, retire the VM.
            4. Create a report(See attachment in BZ).
        testSteps:
            1. Queue the report once the VM has retired
                and check the retirement_requester column for the VM.
        expectedResults:
            1. Requester name must be visible.

    Bugzilla:
        1638502
        1805119
    """
    vm_name, report = vm_retirement_report
    saved_report = report.queue(wait_for_finish=True)

    # filtering the request by description because description sometimes changes with version
    requester_id = (
        appliance.rest_api.collections.requests.filter(
            Q("description", "=", f"VM Retire for: {vm_name}*")
        )
        .resources[0]
        .requester_id
    )

    # obtaining the retirement requester's userid from retirement request
    requester_userid = appliance.rest_api.collections.users.get(id=requester_id).userid

    # the report filter is such that we will only obtain one row in the report
    row_data = saved_report.data.find_row("Name", vm_name)
    assert (
        row_data["Name"],
        row_data["Retirement Requester"],
        row_data["Retirement State"],
    ) == (vm_name, requester_userid, "retired")
