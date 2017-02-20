# -*- coding: utf-8 -*-
from random import sample
import pytest

from utils import testgen
from utils.version import current_version
from utils.soft_get import soft_get
from mgmtsystem.utils import eval_strings

from cfme.containers.container import Container
from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.pod import Pod
from cfme.containers.node import Node
from cfme.containers.provider import ContainersProvider
from cfme.containers.image import Image
from cfme.containers.service import Service
from cfme.containers.image_registry import ImageRegistry


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope="function")


"""
Test container objects properties.
Steps:
    * Go to object detail page, view properties table
Expected results:
    * All fields should have the correct information
    (i.e. equal to the values in the API)
"""


def get_item_if_exist(dict_, *keys):
    """Trying to get fields in the dict 'dict_',
    if getting KeyError, return ''
    """
    out = dict_
    try:
        for key in keys:
            out = out[key]
        return out
    except KeyError:
        return ''


def api_get_project_properties(provider):
    out = {}
    for item in provider.mgmt.api.get('namespace')[1]['items']:
        out[item['metadata']['name']] = {
            'name': item['metadata']['name'],
            'creation_timestamp': item['metadata']['creationTimestamp'],
            'resource_version': item['metadata']['resourceVersion']
        }
    return out


def api_get_image_properties(provider):
    out = {}
    for item in provider.mgmt.o_api.get('image')[1]['items']:
        name = item['dockerImageMetadata']['Config']['Labels']['Name']
        out[name] = {
            'name': name,
            'tag': (item['dockerImageReference'].split(':')[-1]
                    if ':' in item['dockerImageReference'] else ''),
            'full_name': item['dockerImageReference'],
            'architecture': item['dockerImageMetadata']['Architecture'],
            'docker_version': item['dockerImageMetadata']['DockerVersion'],
            'size': item['dockerImageMetadata']['Size'],
            'author': get_item_if_exist(item, 'dockerImageMetadata', 'Author'),
            'entrypoint': get_item_if_exist(item, 'dockerImageMetadata',
                                            'Config', 'Entrypoint', -1)
        }
    return out


def api_get_route_properties(provider):
    out = {}
    for item in provider.mgmt.o_api.get('route')[1]['items']:
        out[item['metadata']['name']] = {
            'name': item['metadata']['name'],
            'creation_timestamp': item['metadata']['creationTimestamp'],
            'resource_version': item['metadata']['resourceVersion'],
            'host_name': item['spec']['host']
        }
    return out


def api_get_pod_properties(provider):
    out = {}
    for item in provider.mgmt.api.get('pod')[1]['items']:
        out[item['metadata']['name']] = {
            'name': item['metadata']['name'],
            'creation_timestamp': item['metadata']['creationTimestamp'],
            'resource_version': item['metadata']['resourceVersion'],
            'phase': item['status']['phase'],
            'restart_policy': get_item_if_exist(item, 'spec', 'restartPolicy'),
            'dns_policy': get_item_if_exist(item, 'spec', 'dnsPolicy'),
            'ip_address': get_item_if_exist(item, 'status', 'podIP')
        }
    return out


def api_get_container_properties(provider):
    out = {}
    for item in provider.mgmt.api.get('pod')[1]['items']:
        for cnt in item['spec']['containers']:
            if cnt['name'] not in out:
                out[cnt['name']] = {
                    'pod_name': item['metadata']['name'],
                    'name': cnt['name'],
                    'privileged': cnt['securityContext']['privileged'],
                    'selinux_level':
                        ''.join(cnt['securityContext']['seLinuxOptions']['level']),
                    'drop_capabilities':
                        ','.join(cnt['securityContext']['capabilities']['drop']),
                    'run_as_user': get_item_if_exist(cnt, 'securityContext', 'runAsUser')
                }
    return out


def api_get_node_properties(provider):
    out = {}
    for item in provider.mgmt.api.get('node')[1]['items']:
        out[item['metadata']['name']] = {
            'name': item['metadata']['name'],
            'creation_timestamp': item['metadata']['creationTimestamp'],
            'number_of_cpu_cores': item['status']['allocatable']['cpu'],
            'max_pods_capacity': item['status']['capacity']['pods'],
            'system_bios_uuid': item['status']['nodeInfo']['systemUUID'],
            'machine_id': item['status']['nodeInfo']['machineID'],
            'runtime_version':
                get_item_if_exist(item, 'status', 'nodeInfo', 'containerRuntimeVersion'),
            'kubelet_version':
                get_item_if_exist(item, 'status', 'nodeInfo', 'kubeletVersion'),
            'proxy_version':
                get_item_if_exist(item, 'status', 'nodeInfo', 'kubeProxyVersion'),
            'kernel_version':
                get_item_if_exist(item, 'status', 'nodeInfo', 'kernelVersion')
        }
    return out


def api_get_service_properties(provider):
    out = {}
    for item in provider.mgmt.api.get('service')[1]['items']:
        out[item['metadata']['name']] = {
            'name': item['metadata']['name'],
            'creation_timestamp': item['metadata']['creationTimestamp'],
            'resource_version': item['metadata']['resourceVersion'],
            'session_affinity': item['spec']['sessionAffinity'],
            'type': get_item_if_exist(item, 'spec', 'type'),
            'portal_ip': get_item_if_exist(item, 'spec', 'portalIP')
        }
    return out


def api_get_image_registry_properties(provider):
    out = {}
    for item in provider.mgmt.list_image_registry():
        if item.host not in ('openshift', 'openshift3'):
            out[item.host] = {
                'host': item.host
            }
    return out


class DataSet(object):
    def __init__(self, obj, get_props_api, polarion_id):
        self.obj = obj
        self.get_props_api = get_props_api
        pytest.mark.polarion(polarion_id)(self)


DataSets = [
    DataSet(Container, api_get_container_properties, 'CMP-9945'),
    DataSet(Project, api_get_project_properties, 'CMP-10430'),
    DataSet(Route, api_get_route_properties, 'CMP-9877'),
    DataSet(Pod, api_get_pod_properties, 'CMP-9911'),
    DataSet(Node, api_get_node_properties, 'CMP-9960'),
    DataSet(Image, api_get_image_properties, 'CMP-9978'),
    DataSet(Service, api_get_service_properties, 'CMP-9890'),
    DataSet(ImageRegistry, api_get_image_registry_properties, 'CMP-9988')
]


@pytest.mark.parametrize('dataset', DataSets, ids=[dataset.obj.__name__ for dataset in DataSets])
def test_properties(provider, dataset):

    props_api = dataset.get_props_api(provider)
    count = len(props_api)
    if not count:
        pytest.skip('No objects to test for {}.'.format(dataset.obj.__name__))
    object_names = sample(props_api.keys(), min(2, count))

    errors = []
    for obj_name in object_names:

        if dataset.obj is Container:
            instance = dataset.obj(obj_name, props_api[obj_name].pop('pod_name'))
        elif dataset.obj is Image:
            instance = dataset.obj(obj_name, props_api[obj_name]['tag'], provider)
        else:
            instance = dataset.obj(obj_name, provider)

        instance.summary.reload()
        props_ui = instance.summary.properties
        for field in props_api[obj_name].keys():

            try:
                row = soft_get(props_ui, field)
            except AttributeError:
                errors.append('Missing field in {}({}) properties table: {}'
                              .format(dataset.obj.__name__, obj_name, field))
                continue

            ui_val, api_val = eval_strings([row.value, props_api[obj_name][field]])

            if api_val != ui_val:
                errors.append('Data integrity error: '
                              '{}({}) - field({}) ui({}) != api({})'
                              .format(dataset.obj.__name__, obj_name,
                               field, ui_val, api_val))

    if errors:
        raise Exception('\n' + '\n'.join(errors))
