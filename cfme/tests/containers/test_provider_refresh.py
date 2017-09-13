import time

import fauxfactory
import pytest

from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.containers.project import Project
from cfme.containers.service import Service
from cfme.containers.replicator import Replicator
from cfme.containers.pod import Pod
from cfme.containers.route import Route
from cfme.containers.container import Container
from cfme.containers.volume import Volume

from utils.appliance.implementations.ui import navigate_to
from utils import testgen


pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.usefixtures("setup_provider_modscope")
]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='module')


"""
NOTE:
    All this usage of SSH calls is a temporary workaround until we implement these
    functionalities in Wrapanapi.
"""


@pytest.fixture(scope='module')
def created_resources(provider, appliance):
    """Generating the new resources. we are creating all the resources first in order to
    use 1 refresh call."""
    # Creating the project
    project_name = fauxfactory.gen_alpha().lower()
    provider.cli.run_command('oc new-project {}'.format(project_name), raise_on_error=True)
    # Creating the deployment configuration. this will create 1 replicator, 1 pod and 1 service:
    service_name = fauxfactory.gen_alpha().lower()  # also the route name
    rc_name = '{}-1'.format(service_name)
    pod_name = '{}-deploy'.format(rc_name)
    container_name = 'deployment'
    deployment_command = 'oc run {} -n {} --image=openshift/hello-openshift --expose ' \
        '--port=8080 --replicas=1'.format(service_name, project_name)
    provider.cli.run_command(deployment_command, raise_on_error=True)
    # Setting route for the service
    provider.cli.run_command('oc create route edge --service={}'.format(service_name),
                             raise_on_error=True)
    # Creating the volume
    persistant_volume_payload = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {'name': fauxfactory.gen_alpha().lower()},
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'capacity': {'storage': '1Gi'},
            'nfs': {
                'path': '/tmp',
                'server': '12.34.56.78'
            }
        },
        'persistentVolumeReclaimPolicy': 'Retain'
    }
    provider.cli.run_command(
        'echo \'{}\' > my_pv_spec.json; oc create -f my_pv_spec.json; rm -f my_pv_spec.json'
        .format(str(persistant_volume_payload).replace('\'', '"')), raise_on_error=True)

    provider.refresh_provider_relationships()
    time.sleep(30)

    return {
        Project: Project(project_name, provider, appliance),
        Service: Service(service_name, project_name, provider, appliance),
        Replicator: Replicator(rc_name, project_name, provider, appliance),
        Pod: Pod(pod_name, project_name, provider, appliance),
        Route: Route(service_name, project_name, provider, appliance),
        Container: Container(container_name, pod_name, appliance),
        Volume: Volume(persistant_volume_payload['metadata']['name'], provider, appliance)
    }


@pytest.fixture(scope='module')
def deleted_resources(provider, appliance, created_resources):
    """Deleting the created resources"""
    provider.cli.run_command('oc delete route {}'.format(created_resources[Service].name),
                             raise_on_error=True)
    provider.cli.run_command('oc delete dc {}'.format(created_resources[Service].name),
                             raise_on_error=True)
    provider.cli.run_command('oc delete service {}'.format(created_resources[Service].name),
                             raise_on_error=True)
    provider.cli.run_command('oc delete pod {}'.format(created_resources[Pod].name),
                             raise_on_error=True)
    provider.cli.run_command('oc delete pv {}'.format(created_resources[Volume].name),
                             raise_on_error=True)
    provider.cli.run_command('oc project default')  # Switching back to default
    provider.cli.run_command('oc delete project {}'.format(created_resources[Project].name),
                             raise_on_error=True)
    provider.refresh_provider_relationships()
    time.sleep(30)
    return created_resources


TEST_ITEMS__CREATE = [
    ContainersTestItem(Project, 'CMP-TBD'),
    ContainersTestItem(Service, 'CMP-TBD'),
    ContainersTestItem(Replicator, 'CMP-TBD'),
    ContainersTestItem(Pod, 'CMP-TBD'),
    ContainersTestItem(Route, 'CMP-TBD'),
    ContainersTestItem(Container, 'CMP-TBD'),
    ContainersTestItem(Volume, 'CMP-TBD')
]

TEST_ITEMS__DELETE = [
    ContainersTestItem(Project, 'CMP-TBD'),
    ContainersTestItem(Service, 'CMP-TBD'),
    ContainersTestItem(Replicator, 'CMP-TBD'),
    ContainersTestItem(Pod, 'CMP-TBD'),
    ContainersTestItem(Route, 'CMP-TBD'),
    ContainersTestItem(Container, 'CMP-TBD'),
    ContainersTestItem(Volume, 'CMP-TBD')
]


@pytest.mark.parametrize('test_item', TEST_ITEMS__CREATE,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS__CREATE])
def test_provider_refresh_create(provider, created_resources, test_item):
    object_name, instance_name = test_item.obj.__name__, created_resources[test_item.obj].name
    projects_view = navigate_to(test_item.obj, 'All')
    if not filter(lambda r: r.name.text == instance_name, projects_view.table.rows()):
        raise Exception('Could not find created {} "{}" in UI'.format(object_name, instance_name))


@pytest.mark.parametrize('test_item', TEST_ITEMS__DELETE,
                         ids=[ContainersTestItem.get_pretty_id(ti) for ti in TEST_ITEMS__DELETE])
def test_provider_refresh_delete(provider, deleted_resources, test_item):
    object_name, instance_name = test_item.obj.__name__, deleted_resources[test_item.obj].name
    projects_view = navigate_to(test_item.obj, 'All')
    if filter(lambda r: r.name.text == instance_name, projects_view.table.rows()):
        raise Exception('{} "{}" was deleted but still appear in UI'
                        .format(object_name, instance_name))
