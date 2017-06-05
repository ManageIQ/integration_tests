import json
import random
import time

import fauxfactory

from itertools import chain

import pytest

import requests

from cfme.containers.image import Image
from cfme.containers.node import Node
from cfme.containers.pod import Pod
from cfme.containers.project import Project
from cfme.containers.provider import ContainersProvider
from cfme.containers.replicator import Replicator
from cfme.containers.service import Service
from cfme.containers.template import Template
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable, paginator, toolbar as tb

from utils.log import logger

from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


TEST_OBJECTS = [Project, Service, Replicator, Pod, Node, Template, Image]

objects_ocp = ['"Namespace"', '"Service"', '"ReplicationController"', '"Pod"',
               '"Node"', '"Template"', '"Image"']

labels_for_objs = ['project', 'service', 'rc', 'pod', 'node', 'template', 'image']


@pytest.fixture(scope="module")
def strip_string(found_item):
    a_string = str(found_item)
    a_exists = a_string[1:-1]
    a_item = a_exists[1:-1]

    return a_item


def create_api_data(provider):

    object_names = []
    obj_endpoints = []
    json_new_payload = []

    # pick a random project name
    # [0] is used to pick a name from the list, not necessarily the first item
    # the project name will be random every time the test is executed

    project_name = str(random.choice(provider.mgmt.list_project())[0])
    # project endpoint
    project_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' \
                       + project_name
    # again, [0] to pull the random name only
    service_name = str(random.choice(provider.mgmt.list_service())[0])
    # project containing previously declared service
    service_name_in_project = [x.project_name for x in provider.mgmt.list_service()
                               if x[0] == service_name][0]
    # service endpoint
    service_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' + \
                       service_name_in_project + '/services/' + service_name

    rc_name = str(random.choice(provider.mgmt.list_replication_controller())[0])
    rc_name_in_project = [x.project_name for x in provider.mgmt.list_replication_controller()
                          if x[0] == rc_name][0]
    # rc endpoint
    rc_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' + rc_name_in_project \
                  + '/replicationcontrollers/' + rc_name
    # PATCH cannot be executed on a pod that is not running,
    pods_list = provider.mgmt.list_container_group()
    pods_all_names = [x[0] for x in pods_list]
    pods_names_revised = filter(lambda ch: 'metrics-deployer' not in ch, pods_all_names)
    pod_name = str(random.choice(pods_names_revised))
    pod_name_in_project = [x.project_name for x in provider.mgmt.list_container_group()
                           if x[0] == pod_name][0]
    # pod endpoint
    pod_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' + \
                   pod_name_in_project + '/pods/' + pod_name

    # picking the master node
    node_name = provider.hostname
    # node endpoint
    node_endpoint = 'https://' + provider.hostname + ':8443/api/v1/nodes/' + provider.hostname
    # template name will be picked randomly
    template_name = str(random.choice(provider.mgmt.list_template())[0])
    template_name_in_project = [
        x.project_name for x in provider.mgmt.list_template() if x[0] == template_name][0]
    # template endpoint
    template_endpoint = 'https://' + provider.hostname + ':8443/oapi/v1/namespaces/' + \
                        template_name_in_project + '/templates/' + template_name
    # image name will be picked randomly
    image_name = str(random.choice(provider.mgmt.list_image_openshift())['name'])
    # image endpoint
    image_endpoint = 'https://' + provider.hostname + ':8443/oapi/v1/images/' + image_name

    object_names.extend([project_name, service_name, rc_name, pod_name, node_name,
                         template_name, image_name])

    obj_endpoints.extend([project_endpoint, service_endpoint, rc_endpoint, pod_endpoint,
                          node_endpoint, template_endpoint, image_endpoint])

    # use different label for each object and generate json
    for obj_name in objects_ocp:
        key_label = fauxfactory.gen_alphanumeric(6)
        value_label = fauxfactory.gen_alphanumeric(6)
        json_payload_format = '{"apiVersion":"v1","kind":' + obj_name + \
                              ',"metadata":{"labels":{' + '"{}"'.format(key_label) + ':' \
                              + '"{}"'.format(value_label) + '}}}'
        json_new_payload.append(json_payload_format)

    return json_new_payload, object_names, obj_endpoints


def check_request_status(provider):
    json_api_payload, obj_api_names, obj_api_endpoints = create_api_data(provider)

    endpoints_json_dict = dict(zip(obj_api_endpoints, json_api_payload))

    headers = {'Authorization': 'Bearer' + ' ' + provider.mgmt.auth,
               'Content-Type': 'application/strategic-merge-patch+json'}

    for key, value in endpoints_json_dict.iteritems():
        req = requests.patch(key, headers=headers, verify=False, data=value)
        assert req.status_code == 200

    new_lbls_list = []

    for index in range(len(json_api_payload)):
        obj = (json.loads(json_api_payload[index])).values()[2]
        new_lbls_list.append(obj)

    # create list of keys and list of values
    new_lbls_list_revised = [x['labels'] for x in new_lbls_list]
    obj_keys_list = list(chain.from_iterable([d.keys() for d in new_lbls_list_revised]))
    obj_values_list = list(chain.from_iterable([d.values() for d in new_lbls_list_revised]))

    return obj_keys_list, obj_values_list, json_api_payload, obj_api_names


def verify_labels(provider):
    obj_keys_list, obj_values_list, json_api_payload, obj_api_names = check_request_status(provider)

    obj_k = map(str, obj_keys_list)
    obj_v = map(str, obj_values_list)
    obj_k_api = [item.lower() for item in obj_k]

    for t_obj in TEST_OBJECTS:
        navigate_to(t_obj, 'All')
        tb.select("List View")
        list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
        if paginator.page_controls_exist():
            paginator.results_per_page(100)
        else:
            logger.warning(
                'Unable to increase results per page')

        if t_obj is Image:
            img_ui = [r for r in list_tbl.rows() if obj_api_names[6] in str(r.id.text)]
            for img in img_ui:
                obj = Image(img.name.text, img.tag.text, provider)
                keys_ui = obj.summary.labels.keys
                if keys_ui:
                    vals_ui = []
                    for key in keys_ui:
                        element = getattr(obj.summary.labels, key)
                        vals_ui.append(element.value)

            key_found = [e for e in keys_ui if e in '\n'.join(obj_k_api)]
            value_found = [e for e in vals_ui if e in '\n'.join(obj_v)]

            key_item = strip_string(key_found)
            val_item = strip_string(value_found)

            dict_ui = dict(zip(keys_ui, vals_ui))
            key, value = key_item, val_item
            assert key in dict_ui and value == dict_ui[key]
        else:
            obj_ui = [r.name.text for r in list_tbl.rows()]
            obj_ui_elem = [x for x in obj_ui if x in obj_api_names]

            for name in obj_ui_elem:
                obj = t_obj(name, provider)
                keys_ui = obj.summary.labels.keys
                if keys_ui:
                    vals_ui = []
                    for key in keys_ui:
                        element = getattr(obj.summary.labels, key)
                        vals_ui.append(element.value)

            key_found = [e for e in keys_ui if e in '\n'.join(obj_k_api)]
            value_found = [e for e in vals_ui if e in '\n'.join(obj_v)]

            key_item = strip_string(key_found)
            val_item = strip_string(value_found)

            dict_ui = dict(zip(keys_ui, vals_ui))
            key, value = key_item, val_item
            assert key in dict_ui and value == dict_ui[key]


@pytest.mark.polarion('CMP-10572')
def test_labels(provider):
    # verify the created labels in CFME
    navigate_to(provider, 'Details')
    tb.select(
        'Configuration',
        'Refresh items and relationships',
        invokes_alert=True)
    sel.handle_alert()

    time.sleep(90)
    tb.select('Reload Current Display')

    verify_labels(provider)
