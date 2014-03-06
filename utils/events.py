#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" Stuff used to configure appliance for event testing

"""

from fixtures import navigation as nav
import re
from lxml import etree
from py.path import local
from selenium.common.exceptions import TimeoutException
from utils.conf import cfme_data


ALL_EVENTS = [
    ('Datastore Analysis Complete', 'datastore_analysis_complete'),
    ('Datastore Analysis Request', 'datastore_analysis_req'),
    ('Host Added to Cluster', 'host_added_to_cluster'),
    ('Host Analysis Complete', 'host_analysis_complete'),
    ('Host Analysis Request', 'host_analysis_req'),
    ('Host Auth Changed', 'host_auth_changed'),
    ('Host Auth Error', 'host_auth_error'),
    ('Host Auth Incomplete Credentials', 'host_auth_incomplete_credentials'),
    ('Host Auth Invalid', 'host_auth_invalid'),
    ('Host Auth Unreachable', 'host_auth_unreachable'),
    ('Host Auth Valid', 'host_auth_valid'),
    ('Host C & U Processing Complete', 'host_c_and_u_processing_complete'),
    ('Host Compliance Check', 'host_compliance_check'),
    ('Host Compliance Failed', 'host_compliance_failed'),
    ('Host Compliance Passed', 'host_compliance_passed'),
    ('Host Connect', 'host_connect'),
    ('Host Disconnect', 'host_disconnect'),
    ('Host Provision Complete', 'host_provision_complete'),
    ('Host Removed from Cluster', 'host_removed_from_cluster'),
    ('Provider Auth Changed', 'provider_auth_changed'),
    ('Provider Auth Error', 'provider_auth_error'),
    ('Provider Auth Incomplete Credentials', 'provider_auth_incomplete_credentials'),
    ('Provider Auth Invalid', 'provider_auth_invalid'),
    ('Provider Auth Unreachable', 'provider_auth_unreachable'),
    ('Provider Auth Valid', 'provider_auth_valid'),
    ('Service Provision Complete', 'service_provision_complete'),
    ('Service Retired', 'service_retired'),
    ('Service Retirement Warning', 'service_retirement_warning'),
    ('Service Start Request', 'service_start_req'),
    ('Service Started', 'service_started'),
    ('Service Stop Request', 'service_stop_req'),
    ('Service Stopped', 'service_stopped'),
    ('Tag Complete', 'tag_complete'),
    ('Tag Parent Cluster Complete', 'tag_parent_cluster_complete'),
    ('Tag Parent Datastore Complete', 'tag_parent_datastore_complete'),
    ('Tag Parent Host Complete', 'tag_parent_host_complete'),
    ('Tag Parent Resource Pool Complete', 'tag_parent_resource_pool_complete'),
    ('Tag Request', 'tag_req'),
    ('Un-Tag Complete', 'untag_complete'),
    ('Un-Tag Parent Cluster Complete', 'untag_parent_cluster_complete'),
    ('Un-Tag Parent Datastore Complete', 'untag_parent_datastore_complete'),
    ('Un-Tag Parent Host Complete', 'untag_parent_host_complete'),
    ('Un-Tag Parent Resource Pool Complete', 'untag_parent_resource_pool_complete'),
    ('Un-Tag Request', 'untag_req'),
    ('VDI Connecting to Session', 'vdi_connecting_to_session'),
    ('VDI Console Login Session', 'vdi_console_login_session'),
    ('VDI Disconnected from Session', 'vdi_disconnected_from_session'),
    ('VDI Login Session', 'vdi_login_session'),
    ('VDI Logoff Session', 'vdi_logoff_session'),
    ('VM Analysis Complete', 'vm_analysis_complete'),
    ('VM Analysis Failure', 'vm_analysis_failure'),
    ('VM Analysis Request', 'vm_analysis_req'),
    ('VM Analysis Start', 'vm_analysis_start'),
    ('VM C & U Processing Complete', 'vm_c_and_u_processing_complete'),
    ('VM Clone Complete', 'vm_clone_complete'),
    ('VM Clone Start', 'vm_clone_start'),
    ('VM Compliance Check', 'vm_compliance_check'),
    ('VM Compliance Failed', 'vm_compliance_failed'),
    ('VM Compliance Passed', 'vm_compliance_passed'),
    ('VM Create Complete', 'vm_create_complete'),
    ('VM Delete (from Disk) Request', 'vm_delete_from_disk_req'),
    ('VM Discovery', 'vm_discovery'),
    ('VM Guest Reboot', 'vm_guest_reboot'),
    ('VM Guest Reboot Request', 'vm_guest_reboot_req'),
    ('VM Guest Shutdown', 'vm_guest_shutdown'),
    ('VM Guest Shutdown Request', 'vm_guest_shutdown_req'),
    ('VM Live Migration (VMOTION)', 'vm_live_migration_vmotion'),
    ('VM Power Off', 'vm_power_off'),
    ('VM Power Off Request', 'vm_power_off_req'),
    ('VM Power On', 'vm_power_on'),
    ('VM Power On Request', 'vm_power_on_req'),
    ('VM Provision Complete', 'vm_provision_complete'),
    ('VM Remote Console Connected', 'vm_remote_console_connected'),
    ('VM Removal from Inventory', 'vm_removal_from_inventory'),
    ('VM Removal from Inventory Request', 'vm_removal_from_inventory_req'),
    ('VM Renamed Event', 'vm_renamed_event'),
    ('VM Reset', 'vm_reset'),
    ('VM Reset Request', 'vm_reset_req'),
    ('VM Retired', 'vm_retired'),
    ('VM Retirement Warning', 'vm_retirement_warning'),
    ('VM Settings Change', 'vm_settings_change'),
    ('VM Snapshot Create Complete', 'vm_snapshot_create_complete'),
    ('VM Snapshot Create Request', 'vm_snapshot_create_req'),
    ('VM Snapshot Create Started', 'vm_snapshot_create_started'),
    ('VM Standby of Guest', 'vm_standby_of_guest'),
    ('VM Standby of Guest Request', 'vm_standby_of_guest_req'),
    ('VM Suspend', 'vm_suspend'),
    ('VM Suspend Request', 'vm_suspend_req'),
    ('VM Template Create Complete', 'vm_template_create_complete')
]

ALL_VM_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("vm_")]
ALL_HOST_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("host_")]
ALL_TAG_EVENTS = [
    event for event in ALL_EVENTS if event[1].startswith("tag_") or event[1].startswith("untag_")
]
ALL_DATASTORE_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("datastore_")]
ALL_PROVIDER_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("provider_")]
ALL_SERVICE_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("service_")]
ALL_VDI_EVENTS = [event for event in ALL_EVENTS if event[1].startswith("vdi_")]


def setup_for_event_testing(ssh_client, db_session, listener_info, providers):
    # FIX THE ENV ERROR IF PRESENT
    if ssh_client.run_command("ruby -v")[0] != 0:
        success = ssh_client.run_command("echo 'source /etc/default/evm' >> .bashrc")[0] == 0
        assert success, "Issuing the patch command was unsuccessful"
        # Verify it works
        assert ssh_client.run_command("ruby -v")[0] == 0, "Patch failed"

    # IMPORT AUTOMATE NAMESPACE
    qe_automate_namespace_xml = "qe_event_handler.xml"
    qe_automate_namespace_script = "qe_event_handler.rb"
    local_automate_script = local(__file__)\
        .new(basename="../data/%s" % qe_automate_namespace_script)\
        .strpath
    local_automate_file = local(__file__)\
        .new(basename="../data/%s" % qe_automate_namespace_xml)\
        .strpath
    tmp_automate_file = "/tmp/%s" % qe_automate_namespace_xml

    # Change the information
    with open(local_automate_file, "r") as input_xml, \
            open(tmp_automate_file, "w") as output_xml:
        tree = etree.parse(input_xml)
        root = tree.getroot()

        def set_text(xpath, text):
            field = root.xpath(xpath)
            assert len(field) == 1
            field[0].text = text
        set_text("//MiqAeSchema/MiqAeField[@name='url']",
                 re.sub(r"^http://([^/]+)/?$", "\\1", listener_info.host))
        set_text("//MiqAeSchema/MiqAeField[@name='port']", str(listener_info.port))

        # Put the custom script from an external file
        with open(local_automate_script, "r") as script:
            set_text("//MiqAeMethod[@name='relay_events']",
                     etree.CDATA(script.read()))

        et = etree.ElementTree(root)
        et.write(output_xml)

    # copy xml file to appliance
    # but before that, let's check whether it's there because we may have already applied this file
    if ssh_client.run_command("ls /root/%s" % qe_automate_namespace_xml)[0] != 0:
        ssh_client.put_file(tmp_automate_file, '/root/')

        # run rake cmd on appliance to import automate namespace
        rake_cmd = "evm:automate:import FILE=/root/%s" % \
            qe_automate_namespace_xml
        return_code, stdout = ssh_client.run_rake_command(rake_cmd)
        try:
            assert return_code == 0, "namespace import was unsuccessful"
        except AssertionError:
            # We didn't successfully do that so remove the file to know
            # that it's needed to do it again when run again
            ssh_client.run_command("rm -f /root/%s" % qe_automate_namespace_xml)
            raise

    # CREATE AUTOMATE INSTANCE HOOK
    if db.session.query(db['miq_ae_instances'].name)\
            .filter(db['miq_ae_instances'].name == "RelayEvents").count() == 0:
        # Check presence
        automate_explorer_pg = nav.automate_explorer_pg()
        parent_class = "Automation Requests (Request)"
        instance_details = [
            "RelayEvents",
            "RelayEvents",
            "relationship hook to link to custom QE events relay namespace"
        ]
        instance_row = 2
        instance_value = "/QE/Automation/APIMethods/relay_events?event=$evm.object['event']"

        class_pg = automate_explorer_pg.click_on_class_access_node(parent_class)
        if not class_pg.is_instance_present("RelayEvents"):
            instance_pg = class_pg.click_on_add_new_instance()
            instance_pg.fill_instance_info(*instance_details)
            instance_pg.fill_instance_field_row_info(instance_row, instance_value)
            class_pg = instance_pg.click_on_add_system_button()
            assert class_pg.flash_message_class == 'Automate Instance "%s" was added' %\
                instance_details[0]

    # IMPORT POLICIES
    policy_yaml = "profile_relay_events.yaml"
    policy_path = local(__file__).new(basename="../data/%s" % policy_yaml)

    home_pg = nav.home_page_logged_in()
    import_pg = home_pg.header.site_navigation_menu("Control")\
        .sub_navigation_menu("Import / Export")\
        .click()
    if not import_pg.has_profile_available("Automate event policies"):
        import_pg = import_pg.import_policies(policy_path.strpath)
        assert import_pg.flash.message == "Press commit to Import"
        import_pg = import_pg.click_on_commit()
        assert "was uploaded successfully" in import_pg.flash.message

    # ASSIGN POLICY PROFILES
    for provider in providers:
        assign_policy_profile_to_infra_provider("Automate event policies", provider)


def assign_policy_profile_to_infra_provider(policy_profile, provider):
    """ Assigns the Policy Profile to a provider

    """
    infra_providers_pg = nav.infra_providers_pg()
    try:
        infra_providers_pg.select_provider(cfme_data['management_systems'][provider]['name'])
    except Exception:
        return
    policy_pg = infra_providers_pg.click_on_manage_policies()
    if not policy_pg.policy_selected(policy_profile):
        policy_pg.select_profile_item(policy_profile)
        try:
            policy_pg.save(visible_timeout=10)
        except TimeoutException:
            pass
        else:
            assert policy_pg.flash.message == 'Policy assignments successfully changed',\
                'Save policy assignment flash message did not match'
