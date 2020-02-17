import pytest

from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider

pytestmark = [
    pytest.mark.manual,
    test_requirements.ansible
]


@pytest.mark.tier(3)
def test_embed_tower_retire_service_with_instances_ec2():
    """
    Retire Service+instances which were deployed by playbook from CFME UI.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_exec_play_against_machine_multi_appliance():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against machine with machine credentials. Deploy 2
    appliances, second one as unconfigured, through appliance_console join
    the
    region of first appliance. Enable embedded ansible on 2nd appliance.
    From first appliance, add scm, credentials, new catalog, catalog item
    of AnsiblePlaybook type. Select playbook e.g. dump_all_vars and order
    it. When asked what machine to run it against, pick any rhel7 machine.
    Playbook should be executed successfully.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_failover():
    """
    Check that ansible fails over to new region correctly

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(2)
def test_embed_ansible_next_gen():
    """
    Follow BZ referenced below for test steps

    Bugzilla:
        1511126

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
@pytest.mark.meta(coverage=[1511017])
@pytest.mark.provider([OpenStackProvider])
def test_embed_tower_exec_play_with_creds(appliance, provider):
    """
    User/Admin is able to execute playbook without creating Job Template
    and can execute it against provider type with provider type credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_ansible_catalog_items():
    """
    test adding new playbook catalogs and items to remote and global
    region

    Bugzilla:
        1449696

    Polarion:
        assignee: sbulage
        casecomponent: Configuration
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_add_private_repo():
    """
    Ability to add private repo with SCM credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_repo_url_validation():
    """
    After all processes are running fill out a new repo with resolvable
    /un-resolvable url, use the validation button to check its correct.

    Bugzilla:
        1478958

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(2)
def test_embed_tower_order_service_extra_vars():
    """
    Bugzilla:
        1444831

    Execute playbook with extra variables which will be passed to Tower.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_playbook_with_already_existing_catalog_item_name():
    """
    Bugzilla:
        1509809

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_playbook_order_credentials_usecredsfromservicedialog():
    """
    Test if creds from Service Dialog are picked up for execution of
    playbook or the default are used(that were set at the time of dialog
    creation)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_playbook_machine_credentials_service_details_sui():
    """
    Bugzilla:
        1540689

    When the service is viewed in my services it should also show that the cloud and
    machine credentials were attached to the service.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_custom_button_order_ansible_playbook_service():
    """
    Bugzilla:
        1449361

    An Ansible Service Playbook can be ordered from a Custom Button

    Polarion:
        assignee: sbulage
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/3h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_overridden_extra_vars():
    """
    Bugzilla:
        1444107

    Once a Ansible Playbook Service Dialog is built, it has default parameters, which can
    be overridden at "ordering" time. Check if the overridden parameters are passed.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@test_requirements.ansible
@pytest.mark.tier(3)
def test_automate_ansible_playbook_method_type_verbosity():
    """

    Bugzilla:
        1542665

    Check if ansible playbook method  can work with different verbosity
    levels.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(2)
def test_embed_tower_playbook_with_retry_interval():
    """

    Bugzilla:
        1626152

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        testSteps:
            1. Enable Embedded Ansible
            2. Add repo - https://github.com/billfitzgerald0120/ansible_playbooks
            3. Import Ansible_StateMachine_Set_Retry
            4. Enable domain
            5. Create Catalog using set_retry_4_times playbook.
            6. Add a dummy dialog
            7. Add a catalog
            8. Add a new Catalog item (Generic Type)
            9. Order service
        expectedResults:
            1. Check Embedded Ansible Role is started.
            2. Check repo is added.
            3.
            4.
            5. Verify in the Catalog playbook set_retry_4_times is used.
            6.
            7.
            8.
            9. Check automation.log to make sure the playbook retry is waiting
            at least 60 seconds before trying again.
    """
    pass


@pytest.mark.tier(2)
def test_embed_tower_playbook_with_retry_method():
    """

    Bugzilla:
        1625047

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        testSteps:
            1. Enable Embedded Ansible
            2. Add repo - https://github.com/billfitzgerald0120/ansible_playbooks
            3. Import Ansible_StateMachine_Set_Retry
            4. Enable domain
            5. Create Catalog using set_retry_4_times playbook.
            6. Add a dummy dialog
            7. Add a catalog
            8. Add a new Catalog item (Generic Type)
            9. Order service
        expectedResults:
            1. Check Embedded Ansible Role is started.
            2. Check repo is added.
            3.
            4.
            5. Verify in the Catalog playbook set_retry_4_times is used.
            6.
            7.
            8.
            9. Check automation.log to make sure the playbook retried 3 times and then ended OK.
    """
    pass
