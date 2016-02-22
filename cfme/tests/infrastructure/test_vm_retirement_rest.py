import datetime
import pytest
import fauxfactory

from cfme.rest import a_provider as _a_provider
from utils.version import appliance_is_downstream
from utils.virtual_machines import deploy_template
from utils.wait import wait_for


@pytest.fixture(scope='function')
def a_provider():
    return _a_provider()


@pytest.fixture(scope='function')
def vm(request, a_provider, rest_api):
    # Don't use cfme.rest.vm because we don't need finalizer and delete vm after test
    provider_rest = rest_api.collections.providers.get(name=a_provider.name)
    vm_name = deploy_template(
        a_provider.key,
        "test_rest_vm_{}".format(fauxfactory.gen_alphanumeric(length=6)))
    provider_rest.action.refresh()
    wait_for(
        lambda: len(rest_api.collections.vms.find_by(name=vm_name)) > 0,
        num_sec=600, delay=5)
    return vm_name


@pytest.mark.uncollectif(lambda: appliance_is_downstream())
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:6943"])
@pytest.mark.parametrize(
    "multiple", [True, False],
    ids=["from_collection", "from_detail"])
def test_retire_vm_now(rest_api, vm, multiple):
    """Test retirement of vm
    Prerequisities:
        * An appliance with ``/api`` available.
        * VM
    Steps:
        * POST /api/vm/<id> (method ``retire``)
    Metadata:
        test_flag: rest
    """
    assert "retire" in rest_api.collections.vms.action.all
    retire_vm = rest_api.collections.vms.get(name=vm)
    if multiple:
        rest_api.collections.vms.action.retire(retire_vm)
    else:
        retire_vm.action.retire()

    def _finished():
        retire_vm.reload()
        # The retirement_state field appears after calling retire method
        try:
            if retire_vm.retirement_state == "retired":
                return True
        except:
            pass
        return False

    wait_for(_finished, num_sec=600, delay=10, message="REST vm retire now")


@pytest.mark.uncollectif(lambda: appliance_is_downstream())
@pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:6943"])
@pytest.mark.parametrize(
    "multiple", [True, False],
    ids=["from_collection", "from_detail"])
def test_retire_vm_future(rest_api, vm, multiple):
    """Test retirement of vm
    Prerequisities:
        * An appliance with ``/api`` available.
        * VM
    Steps:
        * POST /api/vm/<id> (method ``retire``) with the ``retire_date``
    Metadata:
        test_flag: rest
    """

    assert "retire" in rest_api.collections.vms.action.all

    retire_vm = rest_api.collections.vms.get(name=vm)
    date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime('%m/%d/%y')
    future = {
        "date": date,
        "warn": "4",
    }
    date_before = retire_vm.updated_on
    if multiple:
        future.update({'href': retire_vm.href})
        rest_api.collections.vms.action.retire(future)
    else:
        retire_vm.action.retire(future)

    def _finished():
        retire_vm.reload()
        try:
            if retire_vm.updated_on > date_before and retire_vm.retires_on:
                return True
        except:
            pass
        return False

    wait_for(_finished, num_sec=600, delay=10, message="REST vm retire future")
