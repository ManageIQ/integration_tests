import pytest

from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import NodeCollection
from cfme.containers.replicator import Replicator
from utils import testgen, conf
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from utils.version import current_version
from utils.ssh import SSHClient


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='module')

TEST_OBJECTS = [Pod, Replicator, NodeCollection, Service]


def check_labels(test_obj, list_ui, provider, soft_assert):
    for name in list_ui:
        obj = test_obj(name, provider)
        company = obj.summary.labels.company.text_value

        soft_assert(
            company == 'redhat',
            'Expected value for company label is "redhat", got {} instead'.format(company))


@pytest.mark.polarion('CMP-10572')
def test_create_label_check(provider, soft_assert):
    """ This test creates a new label for nodes, pods, replicators,
        and services in Openshift. All objects reside in default namespace.
        Then it pulls relevant objects from the API (those residing in the
        default namespace), selects these objects in CFME, and verifies that
        the newly created label is visible in the Summary page for each object
        that was assigned a label.The label that is being used is company=redhat

    """

    hostname = conf.cfme_data.get('management_systems', {})[provider.key] \
        .get('hostname', [])
    username, password = provider.credentials['token'].principal, \
        provider.credentials['token'].secret

    ssh_client = SSHClient(
        hostname=hostname,
        username=username,
        password=password)

    exit_status_pod = ssh_client.run_command(
        "test_pod=$(oc get pod | awk '{if(NR>1)print $1}'); "
        "oc label pods $test_pod company=redhat")
    assert exit_status_pod == 0

    exit_status_rc = ssh_client.run_command(
        "test_rc=$(oc get rc | awk '{if(NR>1)print $1}'); "
        "oc label rc $test_rc company=redhat")
    assert exit_status_rc == 0

    exit_status_service = ssh_client.run_command(
        "test_service=$(oc get service | awk '{if(NR>1)print $1}'); "
        "oc label services $test_service company=redhat")
    assert exit_status_service == 0

    exit_status_node = ssh_client.run_command(
        "test_node=$(oc get node | awk '{if(NR>1)print $1}'); "
        "oc label nodes $test_node company=redhat")
    assert exit_status_node == 0

    navigate_to(provider, 'Details')
    tb.select(
        'Configuration',
        'Refresh items and relationships',
        invokes_alert=True)
    sel.handle_alert()

    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)

    pod_list_api = provider.mgmt.list_container_group()
    pod_default_api = [
        pod for pod in pod_list_api if pod.project_name == 'default']
    pod_default_names_api = [i[0] for i in pod_default_api]

    rc_list_api = provider.mgmt.list_replication_controller()
    rc_default_api = [rc for rc in rc_list_api if rc.project_name == 'default']
    rc_default_names_api = [i[0] for i in rc_default_api]

    service_list_api = provider.mgmt.list_service()
    service_default_api = [
        service for service in service_list_api if service.project_name == 'default']
    service_default_names_api = [i[0] for i in service_default_api]

    node_default_api = provider.mgmt.list_node()
    node_default_names_api = [i[0] for i in node_default_api]

    for test_obj in TEST_OBJECTS:
        navigate_to(test_obj, 'All')

        list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

        if test_obj is Pod:
            pod_ui = [r.name.text for r in list_tbl.rows()]
            pod_selected_ui = [x for x in pod_ui if x in pod_default_names_api]
            check_labels(test_obj, pod_selected_ui, provider, soft_assert)

        elif test_obj is Replicator:
            rc_ui = [r.name.text for r in list_tbl.rows()]
            rc_selected_ui = [x for x in rc_ui if x in rc_default_names_api]
            check_labels(test_obj, rc_selected_ui, provider, soft_assert)

        elif test_obj is NodeCollection:
            collection = test_obj()
            nodes = collection.all()
            node_ui = [node for node in nodes]
            node_selected_ui = [
                x for x in node_ui if x in node_default_names_api]
            check_labels(test_obj, node_selected_ui, provider, soft_assert)

        else:
            service_ui = [r.name.text for r in list_tbl.rows()]
            service_selected_ui = [
                x for x in service_ui if x in service_default_names_api]
            check_labels(test_obj, service_selected_ui, provider, soft_assert)
