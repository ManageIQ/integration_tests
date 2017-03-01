import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.containers.project import Project
from utils import testgen, version
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from utils import conf
import time


pytestmark = [
    pytest.mark.uncollectif(
        lambda provider: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')

# CMP-10287


def test_create_label_check(ssh_client, provider):
    """ This test creates a new project in Openshift and labels it,
        then it verifies the label exists and is visible on the summary
        page.There is a sufficient time provided so that CFME is updated
        with the latest data
    """

    hostname = conf.cfme_data.get('management_systems', {})[provider.key] \
        .get('hostname', [])
    username, password = provider.credentials['token'].principal, \
        provider.credentials['token'].secret

    ssh_client = ssh_client(
        hostname=hostname,
        username=username,
        password=password)

    exit_status, output = ssh_client.run_command(
        "oc new-project test-new; oc label namespace test-new Risk=High")
    assert exit_status == 0
    assert 'namespace "test-new" labeled' in output

    navigate_to(provider, 'Details')
    tb.select(
        'Configuration',
        'Refresh items and relationships',
        invokes_alert=True)
    sel.handle_alert()
    time.sleep(6)

    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)
    time.sleep(6)

    navigate_to(Project, 'All')
    tb.select('List View')

    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    names = [r.name.text for r in list_tbl.rows() if r == 'test-new']

    for name in names:
        obj = Project(name, provider)
        assert obj.get_detail('Labels', 'Risk') == 'High'
