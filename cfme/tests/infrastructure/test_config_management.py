import fauxfactory
import pytest

from cfme import test_requirements
from cfme.ansible_tower.explorer import TowerCreateServiceDialogFromTemplateView
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.infrastructure.config_management.satellite import SatelliteProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.provider([AnsibleTowerProvider, SatelliteProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider_modscope')
]


TEMPLATE_TYPE = {
    "job": "Job Template (Ansible Tower)",
    "workflow": "Workflow Template (Ansible Tower)",
}


@pytest.fixture
def config_system(provider):
    # by selecting a profile we don't have to select fetch ALL the config systems on a provider
    profile = provider.config_profiles[0]
    return fauxfactory.gen_choice(profile.config_systems)


@pytest.mark.tier(3)
def test_config_manager_detail_config_btn(provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/2h
        casecomponent: Ansible
    """
    provider.refresh_relationships()


@pytest.mark.tier(2)
def test_config_manager_add(provider):
    """
    Polarion:
        assignee: nachandr
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    navigate_to(provider, "Details")


@pytest.mark.tier(3)
def test_config_manager_add_invalid_url(has_no_providers, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    wait_for(lambda: not provider.exists, num_sec=60, delay=3)  # wait for provider to be deleted
    provider.url = 'https://invalid_url'
    error_message = 'getaddrinfo: Name or service not known'
    with pytest.raises(Exception, match=error_message):
        provider.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_creds(has_no_providers, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    wait_for(lambda: not provider.exists, num_sec=60, delay=3)  # wait for provider to be deleted
    provider.credentials.principal = 'invalid_user'
    if provider.type == "ansible_tower":
        msg = ('validation was not successful: {"detail":"Authentication credentials '
               'were not provided. To establish a login session, visit /api/login/."}')
    else:
        msg = 'Credential validation was not successful: 401 Unauthorized'
    with pytest.raises(Exception, match=msg):
        provider.create()


@pytest.mark.tier(3)
def test_config_manager_edit(request, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    new_name = fauxfactory.gen_alpha(8)
    old_name = provider.name
    with update(provider):
        provider.name = new_name
    request.addfinalizer(lambda: provider.update(updates={'name': old_name}))
    assert (provider.name == new_name and provider.exists),\
        "Failed to update configuration manager's name"


@pytest.mark.tier(3)
def test_config_manager_remove(request, provider):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    request.addfinalizer(provider.create)
    provider.delete()


@pytest.mark.tier(3)
def test_config_system_tag(config_system, tag):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    config_system.add_tag(tag=tag, details=False)
    assert tag in config_system.get_tags(), "Added tag not found on configuration system"


@pytest.mark.tier(3)
@pytest.mark.provider([AnsibleTowerProvider], scope='module')
def test_ansible_tower_job_templates_tag(request, provider, tag):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: high

    Bugzilla:
        1673104
    """
    try:
        job_template = provider.appliance.collections.ansible_tower_job_templates.all()[0]
    except IndexError:
        pytest.skip("No job template was found")
    job_template.add_tag(tag=tag, details=False)
    request.addfinalizer(lambda: job_template.remove_tag(tag=tag))
    assert tag in job_template.get_tags(), "Added tag not found on configuration system"


# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass


@pytest.mark.tier(3)
@pytest.mark.provider([AnsibleTowerProvider], scope='module')
@pytest.mark.parametrize('template_type', TEMPLATE_TYPE.values(), ids=list(TEMPLATE_TYPE.keys()))
def test_ansible_tower_service_dialog_creation_from_template(provider, template_type):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: high

    """
    try:
        job_template = provider.appliance.collections.ansible_tower_job_templates.filter(
            {"job_type": template_type}).all()[0]
    except IndexError:
        pytest.skip("No job template was found")
    dialog_label = fauxfactory.gen_alpha(8)
    dialog = job_template.create_service_dailog(dialog_label)
    view = job_template.browser.create_view(TowerCreateServiceDialogFromTemplateView)
    view.flash.assert_success_message('Service Dialog "{}" was successfully created'.format(
        dialog_label))
    assert dialog.exists

    dialog.delete_if_exists()


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_add_multiple_times_ansible_tower_243():
    """
    Try to add same Tower manager twice (use the same IP/hostname). It
    should fail and flash message should be displayed.

    Polarion:
        assignee: nachandr
        caseimportance: medium
        caseposneg: negative
        casecomponent: Ansible
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.tower
def test_config_manager_job_template_refresh():
    """
    After first Tower refresh, go to Tower UI and change name of 1 job
    template. Go back to CFME UI, perform refresh and check if job
    template name was changed.

    Polarion:
        assignee: nachandr
        casecomponent: Ansible
        initialEstimate: 1/2h
    """
    pass


@pytest.mark.manual
@test_requirements.tower
def test_config_manager_accordion_tree():
    """
    Make sure there is accordion tree, once Tower is added to the UI.

    Bugzilla:
        1560552

    Polarion:
        assignee: nachandr
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
        startsin: 5.8
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_remove_objects_ansible_tower_310():
    """
    1) Add Configuration manager
    2) Perform refresh and wait until it is successfully refreshed
    3) Remove provider
    4) Click through accordion and double check that no objects (e.g.
    tower job templates) were left in the UI

    Polarion:
        assignee: nachandr
        caseimportance: medium
        casecomponent: Ansible
        initialEstimate: 1/4h
        startsin: 5.7
    """
    pass


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_change_zone():
    """
    Add Ansible Tower in multi appliance, add it to appliance with UI. Try
    to change to zone where worker is enabled.

    Bugzilla:
        1353015

    Polarion:
        assignee: nachandr
        casecomponent: Provisioning
        caseimportance: medium
        initialEstimate: 1h
        startsin: 5.8
    """
    pass
