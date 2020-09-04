import pytest

from cfme import test_requirements
from cfme.common.provider import BaseProvider
from cfme.infrastructure.provider.scvmm import SCVMMProvider
from cfme.markers.env_markers.provider import all_required
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.wait import TimedOutError


@pytest.mark.tier(2)
@test_requirements.power
@pytest.mark.provider(
    [BaseProvider],
    scope='module',
    required_fields=[['templates', 'small_template']]  # default for create_on_provider
)
@pytest.mark.parametrize('create_vm', ['small_template'], indirect=True)
def test_vm_discovery(provider, create_vm):
    """ Tests whether cfme will discover a vm change (add/delete) without being manually refreshed.

    Polarion:
        assignee: prichard
        casecomponent: Infra
        initialEstimate: 1/4h
        tags: power
        setup:
            1. Desired provider set up
        testSteps:
            1. Create a virtual machine on the provider.
            2. Wait for the VM to appear
            3. Delete the VM from the provider (not using CFME)
            4. Wait for the VM to become Archived.
    """
    if provider.one_of(SCVMMProvider):
        provider.refresh_provider_relationships()

    try:
        create_vm.wait_to_appear(timeout=600, load_details=False)
    except TimedOutError:
        pytest.fail("VM was not found in CFME")

    if provider.one_of(SCVMMProvider):
        provider.refresh_provider_relationships()
    create_vm.mgmt.delete()
    create_vm.wait_for_vm_state_change(desired_state='archived', timeout=720,
                                       from_details=False, from_any_provider=True)


def provider_classes(appliance):
    required_providers = all_required(appliance.version)

    selected = dict(infra=[], cloud=[], container=[])
    # we want to collect these provider categories
    for cat in selected.keys():
        selected[cat].extend(
            {  # quick and dirty uniqueness for types/versions
                prov.klass
                for prov in required_providers
                if prov.category == cat
            }
        )
    return selected


@pytest.mark.tier(0)
@test_requirements.general_ui
@pytest.mark.meta(automates=[BZ(1671844)])
def test_provider_type_support(appliance, soft_assert):
    """Test availability of GCE provider in downstream CFME builds

    Polarion:
        assignee: pvala
        initialEstimate: 1/10h
        casecomponent: WebUI
    """
    classes_to_test = provider_classes(appliance)
    for category, providers in classes_to_test.items():
        try:
            collection = getattr(appliance.collections, providers[0].collection_name)
        except AttributeError:
            msg = 'Missing collection name for a provider class, cannot test UI field'
            logger.exception(msg)
            pytest.fail(msg)
        view = navigate_to(collection, 'Add')
        options = [o.text for o in view.prov_type.all_options]
        for provider_class in providers:
            type_text = provider_class.ems_pretty_name
            if type_text is not None:
                soft_assert(
                    type_text in options,
                    'Provider type [{}] not in Add provider form options [{}]'
                    .format(type_text, options)
                )


@test_requirements.configuration
@pytest.mark.meta(automates=[1625788])
@pytest.mark.provider([BaseProvider], scope="module", selector=ONE)
def test_default_miq_group_is_tenant_group(appliance, create_vm):
    """
    Test whether the
    Tenant.root_tenant.default_miq_group.tenant_group? == true

    Bugzilla:
        1625788

    Polarion:
        assignee: jhenner
        casecomponent: Configuration
        initialEstimate: 1/8h
        startsin: 5.10.0.18
        caseimportance: high
        setup:
            1. Provision a VM on the provider portal and wait for the VM to appear in CFME.
        testSteps:
            1. Navigate to VM's details page and check value of 'Group' under 'Lifecycle' table.
            2. Run 'Tenant.root_tenant.default_miq_group.tenant_group? == true' command in
                rails console and ensure it's success.
    """
    view = navigate_to(create_vm, "Details")
    assert view.entities.summary("Lifecycle").get_text_of("Group") == "Tenant My Company access"
    assert appliance.ssh_client.run_rails_command(
        "Tenant.root_tenant.default_miq_group.tenant_group? == true"
    ).success
