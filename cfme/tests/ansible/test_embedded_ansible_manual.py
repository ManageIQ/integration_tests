import pytest

from cfme import test_requirements

pytestmark = [
    pytest.mark.manual,
    test_requirements.ansible
]


@pytest.mark.tier(1)
def test_embed_tower_dashboard():
    """
    Check dashboard view has been added to existing Tower provider screens

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


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


@pytest.mark.tier(3)
def test_embed_tower_playbooks():
    """
    playbooks included under ansible shown in a table view (automation-
    ansible-playbooks)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
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


@pytest.mark.tier(1)
def test_embed_tower_add_scm_credentials():
    """
    Add SCM credentials for private GIT repo.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_monitor_resources():
    """
    Check there is a method for monitoring embedded ansibles resource
    usage.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/10h
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
def test_embed_tower_exec_play_against_rhos():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against RHOS with RHOS credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_refresh_provider_repo_list():
    """
    Test if ansible playbooks list is updated in the UI when "Refresh
    Selected Ansible Repositories" clicked in the repository list.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_refresh_provider_repo_details():
    """
    Test if ansible playbooks list is updated in the UI when "Refresh this
    Repository" clicked in the repository details view.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(2)
def test_embed_tower_invisible():
    """
    Embedded Ansible Tower provider won"t be visible in the CFME UI (Tower
    should be headless, its UI should not be enabled.) p1

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/12h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_ui_requests_notifications_negative():
    """
    After all processes are running make sure websockets are enabled then
    add a repo with the same name as a current repo and check the
    notifications display correctly. With a Red banner to show it was
    unsuccessful.

    Bugzilla:
        1471868

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_repo_tag():
    """
    RBAC - tag Ansible repo and allow new user see only this repo.

    Bugzilla:
        1526217

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_repo_details():
    """
    test clicking on a repo name should show details of the repository.
    (Automation-Ansible-repositories table view showing added repos)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_exec_play_against_openstack():
    """
    Execute playbook against Openstack provider.
    Workaround must be applied:

    Bugzilla:
        1511017

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_ui_requests_notifications():
    """
    After all processes are running and websockets role is enabled, add a
    new repo to embedded tower and check the notifications display
    correctly. With a Green banner to show it was successful.

    Bugzilla:
        1471868

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_api_auth():
    """
    The Tower API should not be wide open, authentication is required.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_exec_play_against_gce():
    """
    User/Admin is able to execute playbook without creating Job Temaplate
    and can execute it against Google Compute Engine Cloud with GCE
    credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_embed_tower_credentials():
    """
    Credentials included under ansible shown in a table view (automation-
    ansible-credentials)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: critical
        initialEstimate: 1/12h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_creds_details():
    """
    Clicking on a cred name should show details of the Credentials.
    (Automation-Ansible-Credentials Table view showing provider creds
    added)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_ha():
    """
    Tower should be highly available. p2

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_add_azure_credentials():
    """
    Add Azure credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_add_network_credentials():
    """
    Add Network credentials.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
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


@pytest.mark.tier(3)
def test_service_ansible_service_name():
    """
    Bugzilla:
        1505929

    After creating the service using ansible playbook type add a new text
    field to service dialog named "service_name" and then use that service
    to order the service which will have a different name than the service
    catalog item.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/2h
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


@pytest.mark.tier(1)
def test_embed_tower_playbooks_tag():
    """
    Bugzilla:
        1526218

    RBAC - tag playbooks and allow user to see just this taged playbook.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_event_catcher_process():
    """
    EventCatcher process is started after Ansible role is enabled (rails
    evm:status)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/4h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_vault():
    """
    Add vault password and test in the playbook that encrypted yml can be
    decrypted.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_escalate_perm_sudo():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_add_machine_credentials_machine_root_pass():
    """
    Allow user/admin to create/import credentials for machines which will
    be managed (may need to be split into multiple tests to cover
    -Machine, Network, Amazon Web Services, Rackspace, VMware vCenter, Red
    Hat Satellite 6, Red Hat CloudForms, Google Compute Engine, Microsoft
    Azure Classic, Microsoft Azure Resource Manager, OpenStack)

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(1)
def test_embed_tower_creds_tag():
    """
    Bugzilla:
        1526219

    RBAC - tag credentials and allow new user see just this credential.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
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
def test_service_ansible_playbook_cloud_credentials():
    """
    Bugzilla:
        1444092

    When the service is viewed in my services it should also show that the cloud credentials
    were attached to the service.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: low
        initialEstimate: 1/4h
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
def test_service_ansible_playbook_machine_credentials_service_details_opsui():
    """
    Bugzilla:
        1515561

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


@pytest.mark.tier(3)
def test_service_ansible_linked_vms_opsui_sui():
    """
    Associated with BZ

    Bugzilla:
        1510797

    Please follow the steps below to recreate the scenario: 1. Enable
    Embedded Ansible role.
    2. Wait until it will be enabled.
    3. Navigate to Automate/Ansible.
    4. Add ansible repository https://github.com/mkanoor/playbook.
    5. Navigate to Services->Catalogs.
    6. Expand "Catalog Items" accordion.
    7. Create "Ansible Playbook" Catalog Item.
    8. Pick "add_single_vm_to_service.yml" playbook.
    9. Navigate to Control->Explorer.
    10. Expand Actions accordion.
    11. Click Configuration->Add a new Action.
    12. In action type choose "Run Ansible Playbook".
    13. In Playbook Catalog Item choose just created catalog item.
    14. In inventory choose "Target machine" or provide a specific host.
    15. Assign this action to some event in a host or vm control policy.
    16. Assign policy profile which contains that policy to some host or
    vm.
    17. Trigger the event which assigned to the policy.
    18. Wait until the service will be provisioned.
    19. Navigate tot Services/My Services.
    20. Open details of the provisioned service, open "Provisioning" tab.

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_playbook_standard_output_non_ascii_hostname():
    """
    Look for Standard ouptut

    Bugzilla:
        1534039

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        caseimportance: medium
        initialEstimate: 1/6h
        tags: ansible_embed
    """
    pass


@pytest.mark.tier(3)
def test_service_ansible_playbook_retire_non_ascii():
    """
    Retire ansible playbook service with non_ascii host

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
def test_embed_tower_repo_add_remote_zone():
    """
    Test whether repository or credentials on New Zone.

    Bugzilla:
        1656308

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        testSteps:
            1. Configure a CFME appliance with the Embedded Ansible provider
            2. Create a new zone
            3. Move the appliance into the new zone
            4. Add an embedded Ansible repository or credential
        expectedResults:
            1. Check Embedded Ansible Role is started.
            2.
            3.
            4. Check Repository or Credentials were added.
    """
    pass


@pytest.mark.tier(2)
def test_automate_ansible_playbook_method_copy():
    """
    When copying a method within the automate model the copied method
    does not have the Embedded Methods that are a part of the source method

    Bugzilla:
        1592140

    Polarion:
        assignee: sbulage
        casecomponent: Ansible
        initialEstimate: 1/2h
        testSteps:
            1. Configure a CFME appliance with the Embedded Ansible provider
            2. Create Catalog item.
            3. Create catalog.
            4. Create Domain.
            5. Create Method.
            6. Create another domain.
            7. Copy above method.
        expectedResults:
            1. Check Embedded Ansible Role is started.
            2. Check catalog item is created.
            3. Check catalog is added.
            4. Check Domain is added.
            5. Check method is added.
            6. check second Domain attached.
            7. Check method is being copied along with Path.
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
