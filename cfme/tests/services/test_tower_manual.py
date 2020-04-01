"""Manual tests"""
import pytest

from cfme import test_requirements


@pytest.mark.manual
@test_requirements.tower
@pytest.mark.tier(1)
def test_config_manager_override_extra_vars_dialog_vsphere():
    """
    1. Add tower 2.4.3 provider and perform refresh
    2. Go to job templates
    3. Create service dialog from third_job_template
     - this template is bound to vsphere55 inventory
     - simple_play_4_dockers.yaml playbook is part of this template
     - this playbook will touch /var/tmp/touch_from_play.txt
     - into /var/tmp/touch_from_play_dumped_vars.txt all variables
       available during play run will be dumped
     - this includes also variables passed from Tower or CFME
     - this project is linked with Tower and Vsphere55 credentials
     - Vsphere55 credentials are used when inventory is retrieved
     - Tower credentials are the creds used to login into VM which will be
       deployed
     - Vsphere template used for VM deployment must have ssh key "baked" in
       Prompt for Extra variables must be enabled.
    4. Add Vsphere55 provider into CFME and perform refresh
    5. Create new Catalog
    6. Add new catalog item for Vsphere vcentre - VMWare
    7. Provisioning entry point:
       /Service/Provisioning/StateMachines/ServiceProvision_Template/CatalogI
       temInitialization
       Request info tab:
       - Name of template: template_Fedora-Cloud-Base-23-vm-tools_v4 (this
         template has ssh key which matches with Tower creentials)
       - VM Name: test_tower_pakotvan_1234 (it must start with test_tower_ -
         inventory script on Tower 2.4.3 was modified to look only for such VMs
         in order to speed up provisioning)
       Envirnment tab:
       - Select where VM would be placed (Datastore, Host etc.)
       Hardware:
       - Select at least 1GB ram for our template
       Network:
       - vLAN: VM Network
    8. Automate -> Explorer
    9. Add new Domain
    10. Copy instance Infrastructure->Vm->Provisioning->StateMachines->
        VM Provision_VM->Provision_VM from Template into your domain
    11. Edit this instance:
        Look for PostProvision in the first field/column and the following in the
        Value column:
        /ConfigurationManagement/AnsibleTower/Operations/StateMachines/Job/def
        ault?job_template_name=third_job_template
    12. Automate -> Customization -> Service dialogs -> tower_dialog
        Edit this dialog
        Extra variables:
        - make elements in extra variables writable (uncheck readonly).
        - add new element add 1 extra variable - variables must start with
          param_prefix, otherwised will be ignored!!!
    13. Order service
        Enter the exact name of your VM in the limit field:  test_tower_pakotvan_1234
    14. Login to provisioned VM and run`'cat /var/tmp/touch_from_play_dumped_vars.txt'
      ` and grep for variables which were passed from CFME UI.

    Polarion:
        assignee: nachandr
        casecomponent: Cloud
        caseimportance: medium
        initialEstimate: 1d
        startsin: 5.7
    """
    pass
