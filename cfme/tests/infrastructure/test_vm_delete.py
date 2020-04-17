import pytest

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.provider([RHEVMProvider], scope="module"),
    pytest.mark.usefixtures('setup_provider'),
    test_requirements.rhev
]


@pytest.mark.meta(automates=[1592430])
def test_delete_vm_on_provider_side(create_vm, provider):
    """ Delete VM on the provider side and refresh relationships in CFME

    Polarion:
        assignee: jhenner
        initialEstimate: 1/4h
        casecomponent: Infra

    Bugzilla:
        1592430
    """
    logs = LogValidator("/var/www/miq/vmdb/log/evm.log", failure_patterns=[".*ERROR.*"])
    logs.start_monitoring()
    create_vm.cleanup_on_provider()
    provider.refresh_provider_relationships()
    try:
        wait_for(provider.is_refreshed, func_kwargs={'refresh_delta': 10}, timeout=600)
    except TimedOutError:
        pytest.fail("Provider failed to refresh after VM was removed from the provider")
    assert logs.validate(wait="60s")
