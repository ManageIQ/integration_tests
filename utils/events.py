#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" Stuff used to configure appliance for event testing

"""

from fixtures import navigation as nav
import re
import db
from lxml import etree
from py.path import local
from selenium.common.exceptions import TimeoutException
from utils.conf import cfme_data


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
    if db_session.query(db.MiqAeInstance.name)\
            .filter(db.MiqAeInstance.name == "RelayEvents").count() == 0:   # Check presence
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
