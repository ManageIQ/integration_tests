import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.containers.node import Node
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

# CMP-10572


def test_create_label_check(ssh_client, provider):
    """ This test creates a new label on the master node in Openshift,
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

    ssh_client.run_command(
        "master_node=$(oc get nodes | awk 'NR==2' | sed -e 's/\s.*$//'); "
        "oc label nodes $master_node kube=master-new")

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

    navigate_to(Node, 'All')
    tb.select('List View')

    list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    names = [r.name.text for r in list_tbl.rows()]
    remove_names = [1, 2]
    names = [v for i, v in enumerate(names) if i not in remove_names]

    for name in names:
        obj = Node(name, provider)
        obj.summary.reload()
        labels_all = obj.summary.labels
        lbls_cfme = list(labels_all)
        lbls_cfme_new = [i for j in lbls_cfme for i in j]
        lst_lbls_found = ['kube', 'master-new']
        found = any(x in lst_lbls_found for x in lbls_cfme_new)
        assert found
