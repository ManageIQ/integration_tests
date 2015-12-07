from cfme.web_ui import menu
# from cfme.fixtures import pytest_selenium as sel
from fixtures.pytest_store import store
from py.path import local
from utils.path import data_path
from cfme.fixtures import pytest_selenium as sel

"""
SCP the below mentioned files to the respective places for the setup

default:
========
product/menubar/custom_redhat_section.yml
product/menubar/custom_redhat.yml
product/menubar/custom_redhat_courses.yml
db/fixtures/miq_product_features/redhat-miq_product_features.yml


top-right:
==========
product/menubar/top_right_news.yml
product/menubar/top_right_news_cnn.yml
db/fixtures/miq_product_features/top_right_news_features.yml
"""

sections = {
    ('redhat', 'Red Hat'): (

        ('rh_homepage', 'Homepage'),
        ('rh_courses', 'Courses')
    )
}

files_path = data_path.join("menu_plugin")
vmdb_path = local("/var/www/miq/vmdb")


def menu_plugin_setup():
    # Copying the files from menu_plugin folder to their respective locations
    with store.current_appliance.ssh_client as ssh:
        # default module section
        status, result = ssh.run_command(
            "find {} -type d -ls | grep 'menubar'".format(vmdb_path.join("product")))
        if bool(status):
            ssh.run_command("mkdir /var/www/miq/vmdb/product/menubar")
        ssh.put_file(files_path.join("/custom_redhat_section.yml").strpath,
            vmdb_path.join("/product/menubar/custom_redhat_section.yml").strpath)
        ssh.put_file(files_path.join("/custom_redhat.yml").strpath,
            vmdb_path.join("/product/menubar/custom_redhat.yml").strpath)
        ssh.put_file(files_path.join("/custom_redhat_courses.yml").strpath,
            vmdb_path.join("/product/menubar/custom_redhat_courses.yml").strpath)
        status, result = ssh.run_command(
            "find {} -type d -ls | grep 'miq_product_features'".format(vmdb_path.join(
                "db/fixtures")))
        if bool(status):
            ssh.run_command("mkdir /var/www/miq/vmdb/db/fixtures/miq_product_features")
        ssh.put_file(files_path.join("/redhat-miq_product_features.yml").strpath,
            vmdb_path.join(
                "/db/fixtures/miq_product_features/redhat-miq_product_features.yml").strpath)
        # Restarting the evmserverd to reflect the changes
        store.current_appliance.restart_evm_service(rude=True)
    menu_plugin_module_link_setup()
    sel.force_navigate("dashboard")


def menu_plugin_module_link_setup():
    new_branch = menu.branch_convert(sections)
    menu.nav.add_branch('toplevel', new_branch)


def menu_plugin_teardown():
    with store.current_appliance.ssh_client as ssh:
        # default module section
        ssh.run_command("rm -rf {}".format(vmdb_path.join(
            "/product/menubar/custom_redhat_section.yml").strpath))
        ssh.run_command("rm -rf {}".format(vmdb_path.join(
            "/product/menubar/custom_redhat.yml").strpath))
        ssh.run_command("rm -rf {}".format(vmdb_path.join(
            "/product/menubar/custom_redhat_courses.yml").strpath))
        ssh.run_command("rm -rf {}".format(vmdb_path.join(
            "/db/fixtures/miq_product_features/redhat-miq_product_features.yml").strpath))
        # Restarting the evmserverd to reflect the changes
        store.current_appliance.restart_evm_service(rude=True)
    sel.force_navigate("dashboard")


def menu_plugin_assert():
    """
    Existing framework doesnot expose switch_to_frame method of selenium in the browser class.
    So, adding this method here as this is not used much in any other testcase.
    If required this can be moved to browser class later on, based on the requirement.
    """
    sel.browser().switch_to_frame(sel.browser().find_element_by_tag_name("iframe"))
    assert((sel.browser().find_element_by_xpath("//div[@id='legal']/div/div")),
        "Copyright Information not found")
    sel.browser().switch_to_default_content()
    sel.force_navigate('dashboard')
