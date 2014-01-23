from utils import conf
from utils.providers import infra_provider_type_map
from utils.wait import wait_for
import pytest

pytestmark = [pytest.mark.nondestructive,
              pytest.mark.usefixtures("setup_infrastructure_providers"),
              pytest.mark.usefixtures("maximized")]

FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'

HOST_TYPES = ('rhev', 'rhel', 'esx', 'esxi')


def fetch_list(data):
    tests = []
    for provider in data["management_systems"]:
        prov_data = data['management_systems'][provider]
        if prov_data["type"] not in infra_provider_type_map:
            continue
        if not prov_data.get('hosts', None):
            continue

        for host in prov_data["hosts"]:
            if not host.get('test_fleece', False):
                continue

            assert host.get('type', None) in HOST_TYPES,\
                'host type must be set to [%s] for smartstate analysis tests'\
                % ('|'.join(HOST_TYPES))
            tests.append([provider, host['type'], host['name']])
    return tests


def pytest_generate_tests(metafunc):
    argnames = []
    if 'host_name' in metafunc.fixturenames:
        argnames = ['provider', 'host_type', 'host_name']
        argvalues = fetch_list(conf.cfme_data)
        metafunc.parametrize(argnames, argvalues, scope="module")


def get_host_by_name(host_name):
    for provider in conf.cfme_data['management_systems']:
        for host in conf.cfme_data['management_systems'][provider].get('hosts', []):
            if host_name == host['name']:
                return host
    return None


def add_host_credentials(infra_hosts_pg, host_name):
    '''Add host credentials
    '''
    host = get_host_by_name(host_name)
    host_detail_pg = infra_hosts_pg.edit_host_and_save(host)
    assert 'Host "%s" was saved' % host_name in host_detail_pg.flash.message,\
        FLASH_MESSAGE_NOT_MATCHED
    host_detail_pg.flash.click()
    return host_detail_pg


def is_host_analysis_finished_with_refresh(conf_tasks_pg, host_name):
    '''Check if analysis is finished - if not, reload page
    '''
    tasks = conf_tasks_pg.task_list.items
    for task in tasks:
        if task.task_name == "SmartState Analysis for '%s'" % host_name\
                and task.state == 'Finished':
            return True
    conf_tasks_pg.task_buttons.reload()
    return False


def test_run_host_analysis(infra_hosts_pg, provider, host_name, host_type, register_event):
    '''Run host SmartState analysis
    '''
    infra_hosts_pg.wait_for_host_or_timeout(host_name)
    # Add host credentials if needed
    if infra_hosts_pg.quadicon_region.get_quadicon_by_title(host_name).valid_credentials:
        host_detail_pg = infra_hosts_pg.click_host(host_name)
    else:
        host_detail_pg = add_host_credentials(infra_hosts_pg, host_name)
    register_event(None, "host", host_name, ["host_analysis_request", "host_analysis_complete"])
    # Initiate analysis
    host_detail_pg.click_on_smartstate_analysis_and_confirm()
    assert '"%s": Analysis successfully initiated' % host_name\
        in host_detail_pg.flash.message, FLASH_MESSAGE_NOT_MATCHED
    # Wait for the task to finish
    conf_tasks_pg = host_detail_pg.header\
        .site_navigation_menu('Configure')\
        .sub_navigation_menu('Tasks')\
        .click()
    assert conf_tasks_pg.is_the_current_page
    conf_tasks_pg = conf_tasks_pg.load_my_other_tasks_tab()
    conf_tasks_pg._wait_for_results_refresh()
    wait_for(is_host_analysis_finished_with_refresh,
        func_args=[conf_tasks_pg, host_name], delay=10, num_sec=120)
    # Delete all tasks
    conf_tasks_pg.task_buttons.delete_all()


def test_check_host_analysis_results(infra_hosts_pg, provider, host_name, host_type):
    '''Check the results in host detail
    '''
    host_detail_pg = infra_hosts_pg.click_host(host_name)
    cfg_section = host_detail_pg.details.get_section('Configuration')

    assert cfg_section.get_item('Services').value != '0', 'No services found in host detail'

    if host_type in ('rhel', 'rhev'):
        sec_section = host_detail_pg.details.get_section('Security')
        assert sec_section.get_item('Users').value != '0',\
            'No users found in host detail'
        assert sec_section.get_item('Groups').value != '0',\
            'No groups found in host detail'
        assert cfg_section.get_item('Packages').value != '0',\
            'No packages found in host detail'

    elif host_type in ('esx', 'esxi'):
        assert cfg_section.get_item('Advanced Settings').value != '0',\
            'No advanced settings found in host detail'
        sec_accordion = host_detail_pg.accordion_region.accordion_by_name('Security')
        if sec_accordion.is_collapsed:
            sec_accordion.click()
        # This fails for vsphere4...  https://bugzilla.redhat.com/show_bug.cgi?id=1055657
        firewall_rules = sec_accordion.active_link_by_name("Firewall Rules")
        assert firewall_rules, "'Firewall Rules' not found among active links"
        assert "(0)" not in firewall_rules.name,\
            "No firewall rules found in host detail accordion"
