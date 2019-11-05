import fauxfactory
import pytest

from cfme import test_requirements
from cfme.ansible_tower.explorer import TowerCreateServiceDialogFromTemplateView
from cfme.utils.testgen import config_managers
from cfme.utils.testgen import generate
from cfme.utils.update import update


pytest_generate_tests = generate(gen_func=config_managers)

TEMPLATE_TYPE = {
    "job": "Job Template (Ansible Tower)",
    "workflow": "Workflow Template (Ansible Tower)",
}


@pytest.fixture
def config_manager(config_manager_obj, appliance):
    """ Fixture that provides a random config manager and sets it up"""
    config_manager_obj.appliance = appliance
    config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.fixture
def config_system(config_manager):
    return fauxfactory.gen_choice(config_manager.systems)


@pytest.mark.tier(3)
def test_config_manager_detail_config_btn(request, config_manager):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/2h
        casecomponent: Ansible
    """
    config_manager.refresh_relationships()


@pytest.mark.tier(2)
def test_config_manager_add(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        casecomponent: Ansible
        initialEstimate: 1/4h
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_url(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.url = 'https://invalid_url'
    error_message = 'getaddrinfo: Name or service not known'
    with pytest.raises(Exception, match=error_message):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_add_invalid_creds(request, config_manager_obj):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    request.addfinalizer(config_manager_obj.delete)
    config_manager_obj.credentials.principal = 'invalid_user'
    if config_manager_obj.type == "Ansible Tower":
        msg = ('validation was not successful: {"detail":"Authentication credentials '
               'were not provided. To establish a login session, visit /api/login/."}')
    else:
        msg = 'Credential validation was not successful: 401 Unauthorized'
    with pytest.raises(Exception, match=msg):
        config_manager_obj.create()


@pytest.mark.tier(3)
def test_config_manager_edit(request, config_manager):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    new_name = fauxfactory.gen_alpha(8)
    old_name = config_manager.name
    with update(config_manager):
        config_manager.name = new_name
    request.addfinalizer(lambda: config_manager.update(updates={'name': old_name}))
    assert (config_manager.name == new_name and config_manager.exists),\
        "Failed to update configuration manager's name"


@pytest.mark.tier(3)
def test_config_manager_remove(config_manager):
    """
    Polarion:
        assignee: nachandr
        caseimportance: medium
        initialEstimate: 1/15h
        casecomponent: Ansible
    """
    config_manager.delete()


# Disable this test for Tower, no Configuration profiles can be retrieved from Tower side yet
@pytest.mark.tier(3)
@test_requirements.tag
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type == "Ansible Tower")
def test_config_system_tag(request, config_system, tag, appliance):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Ansible
    """
    config_system.add_tag(tag=tag, details=False)
    assert tag in config_system.get_tags(), "Added tag not found on configuration system"


@pytest.mark.tier(3)
@test_requirements.tag
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type != "Ansible Tower")
def test_ansible_tower_job_templates_tag(request, config_manager, tag):
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
        job_template = config_manager.appliance.collections.ansible_tower_job_templates.all()[0]
    except IndexError:
        pytest.skip("No job template was found")
    job_template.add_tag(tag=tag, details=False)
    request.addfinalizer(lambda: job_template.remove_tag(tag=tag))
    assert tag in job_template.get_tags(), "Added tag not found on configuration system"


# def test_config_system_reprovision(config_system):
#    # TODO specify machine per stream in yamls or use mutex (by tagging/renaming)
#    pass


@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda config_manager_obj: config_manager_obj.type != "Ansible Tower")
@pytest.mark.parametrize('template_type', TEMPLATE_TYPE.values(), ids=list(TEMPLATE_TYPE.keys()))
def test_ansible_tower_service_dialog_creation_from_template(request, config_manager, appliance,
        template_type):
    """
    Polarion:
        assignee: nachandr
        initialEstimate: 1/4h
        casecomponent: Ansible
        caseimportance: high

    """
    try:
        job_template = config_manager.appliance.collections.ansible_tower_job_templates.filter(
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
