'''
CFME automation to setup reference architecture
See https://access.redhat.com/site/articles/411683
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from unittestzero import Assert


FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'


@pytest.mark.usefixtures("maximized")
def test_import_policies(request, control_importexport_pg, cfme_data):
    '''Import policies
    '''
    policy_file = cfme_data.data['policies']['import']
    policy_file = "%s/%s" % (request.session.fspath, policy_file)

    control_importexport_pg = control_importexport_pg.import_policies(
        policy_file)
    Assert.equal(control_importexport_pg.flash.message,
        "Press commit to Import")
    control_importexport_pg = control_importexport_pg.click_on_commit()
    Assert.equal(control_importexport_pg.flash.message,
        "Import file was uploaded successfully")


@pytest.mark.usefixtures("maximized")
def test_policy_assignment(infra_providers_pg, provider):
    '''Assigns policy profile(s) defined in cfme_data to management system
    '''
    infra_providers_pg.select_provider(provider["name"])
    policy_pg = infra_providers_pg.click_on_manage_policies()
    for profile in provider["policy_profiles"]:
        policy_pg.select_profile_item(profile)
    policy_pg.save()
    Assert.contains('Policy assignments successfully changed',
        policy_pg.flash.message,
        FLASH_MESSAGE_NOT_MATCHED)


@pytest.mark.skip_selenium
def test_import_namespace(request, cfme_data, ssh_client):
    ''''Import automate method namespace (rake method)
    '''
    filename = cfme_data.data['automate']['import']['file']
    automate_path = cfme_data.data['automate']['import']['path']
    automate_file = "%s/%s/%s" % \
        (request.session.fspath, automate_path, filename)

    # copy xml file to appliance
    ssh_client.put_file(automate_file, '/root/')
    # run rake cmd on appliance to import automate namespace
    rake_cmd = "evm:automate:import FILE=/root/%s" % filename
    ssh_client.run_rake_command(rake_cmd)


@pytest.mark.usefixtures("maximized")
def test_automate_instance_hook(cfme_data, automate_explorer_pg):
    '''Add automate instance that follows relationship to custom namespace
    '''
    instance = cfme_data.data['automate']['instance']

    class_pg = automate_explorer_pg.click_on_class_access_node(
        instance['parent_class'])
    instance_pg = class_pg.click_on_add_new_instance()
    instance_pg.fill_instance_info(*instance['details'])
    instance_pg.fill_instance_field_row_info(
        instance['hook']['row'], instance['hook']['value'])
    class_pg = instance_pg.click_on_add_system_button()
    Assert.equal(class_pg.flash_message_class,
        'Automate Instance "%s" was added' % instance['details'][0])
