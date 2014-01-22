import pytest
import re
from lxml import etree
from py.path import local
from selenium.common.exceptions import TimeoutException
import utils.providers as providers


@pytest.fixture(scope="module",  # IGNORE:E1101
                params=providers.list_infra_providers())
def mgmt_sys(request, cfme_data):
    param = request.param
    return cfme_data['management_systems'][param]


@pytest.mark.smoke
def test_workaround_for_RHEV(ssh_client):
    """ Source correct environment.

    This is for removing an issue with RHEV-M appliances, which
    do not have the correct environment sourced and thus do not work.
    """
    if ssh_client.run_command("ruby -v")[0] == 0:
        pytest.skip(msg="No need to patch")

    success = ssh_client.run_command("echo 'source /etc/default/evm' >> .bashrc")[0] == 0
    assert success, "Issuing the patch command was unsuccessful"
    # Verify it works
    assert ssh_client.run_command("ruby -v")[0] == 0, "Patch failed"


@pytest.mark.smoke
def test_import_namespace(ssh_client, listener_info):
    """ Namespace import

    This fixture imports the ``qe_event_handlers.xml`` file into the machine.
    It also modifies the listener host and port in the xml.
    """
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
    if ssh_client.run_command("ls /root/%s" % qe_automate_namespace_xml)[0] == 0:
        # It's there so skip it
        pytest.skip(msg="No need to upload the namespace")
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


@pytest.mark.smoke
def test_create_automate_instance_hook(maximized, automate_explorer_pg):
    """ Add automate instance that follows relationship to custom namespace

    """
    parent_class = "Automation Requests (Request)"
    instance_details = [
        "RelayEvents",
        "RelayEvents",
        "relationship hook to link to custom QE events relay namespace"
    ]
    instance_row = 2
    instance_value = "/QE/Automation/APIMethods/relay_events?event=$evm.object['event']"

    class_pg = automate_explorer_pg.click_on_class_access_node(parent_class)
    if class_pg.is_instance_present("RelayEvents"):
        pytest.skip(msg="Instance already present")
    instance_pg = class_pg.click_on_add_new_instance()
    instance_pg.fill_instance_info(*instance_details)
    instance_pg.fill_instance_field_row_info(instance_row, instance_value)
    class_pg = instance_pg.click_on_add_system_button()
    assert class_pg.flash_message_class == 'Automate Instance "%s" was added' % instance_details[0]


@pytest.mark.smoke
@pytest.mark.requires("create_automate_instance_hook")
def test_import_policies(request, maximized, home_page_logged_in):
    """ Import policy profile that raises automate model based on events

    Skipped when preceeding test (create_automate_instance_hook) skips.
    No other way of skipping is probably possible.
    """
    policy_yaml = "profile_relay_events.yaml"
    policy_path = local(__file__).new(basename="../data/%s" % policy_yaml)

    home_pg = home_page_logged_in
    import_pg = home_pg.header.site_navigation_menu("Control")\
        .sub_navigation_menu("Import / Export")\
        .click()
    if import_pg.has_profile_available("Automate event policies"):
        pytest.skip(msg="Already imported!")
    import_pg = import_pg.import_policies(policy_path.strpath)
    assert import_pg.flash.message == "Press commit to Import"
    import_pg = import_pg.click_on_commit()
    assert import_pg.flash.message == "Import file was uploaded successfully"


@pytest.mark.smoke
def test_assign_policy_profile(maximized,
                               setup_infrastructure_providers,
                               infra_providers_pg,
                               mgmt_sys):
    """ Assign policy profile to management system

    """
    policy_profile = "Automate event policies"
    infra_providers_pg.select_provider(mgmt_sys['name'])
    policy_pg = infra_providers_pg.click_on_manage_policies()
    policy_pg.select_profile_item(policy_profile)
    try:
        policy_pg.save(visible_timeout=15)
    except TimeoutException:
        pytest.skip(msg="Automate event policies already set.")

    assert policy_pg.flash.message == 'Policy assignments successfully changed',\
        'Save policy assignment flash message did not match'
