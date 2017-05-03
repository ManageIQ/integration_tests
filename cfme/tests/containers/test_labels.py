import json
import random
import re
import time
import fauxfactory
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
from cfme.web_ui import CheckboxTable, toolbar as tb

from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    [ContainersProvider], scope='function')


TEST_OBJECTS = [Project, Service, Replicator, Pod, Node, Image, Template]

objects_ocp = ['"Namespace"', '"Service"', '"ReplicationController"', '"Pod"',
               '"Node"', '"Image"', '"Template"']


def create_api_data(provider):

    object_names = []

    obj_keys_list = []

    obj_values_list = []

    obj_endpoints = []

    # pick a random project name
    # [0] is used to pick a name from the list, not necessarily the first item
    # the project name will be random every time the test is executed

    project_name = str(random.choice(provider.mgmt.list_project())[0])
    # project endpoint
    project_endpoint = 'https://' + provider.hostname + \
        ':8443/api/v1/namespaces/' + project_name

    # again, [0] to pull the random name only
    service_name = str(random.choice(provider.mgmt.list_service())[0])
    # project containing previously declared service
    service_name_in_project = [
        x.project_name for x in provider.mgmt.list_service() if x[0] == service_name][0]
    # service endpoint
    service_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' + \
        service_name_in_project + '/services/' + service_name

    rc_name = str(
        random.choice(
            provider.mgmt.list_replication_controller())[0])
    rc_name_in_project = [x.project_name for x in provider.mgmt.list_replication_controller() if x[
        0] == rc_name][0]
    # rc endpoint
    rc_endpoint = 'https://' + provider.hostname + ':8443/api/v1/namespaces/' + \
        rc_name_in_project + '/replicationcontrollers/' + rc_name

    # PATCH cannot be executed on a pod that is not running, thus excluding
    # 'metrics-deployer' pod
    pods_list = provider.mgmt.list_container_group()
    pods_all_names = [x[0] for x in pods_list]
    pods_names_revised = filter(
        lambda ch: 'metrics-deployer' not in ch,
        pods_all_names)
    pod_name = str(random.choice(pods_names_revised))
    pod_name_in_project = [x.project_name for x in provider.mgmt.list_container_group()
                           if x[0] == pod_name][0]
    # pod endpoint
    pod_endpoint = 'https://' + provider.hostname + \
        ':8443/api/v1/namespaces/' + pod_name_in_project + '/pods/' + pod_name

    # picking master for a node
    node_name = provider.hostname
    # node endpoint
    node_endpoint = 'https://' + provider.hostname + \
        ':8443/api/v1/nodes/' + provider.hostname

    # image name will be picked randomly
    image_name = str(
        random.choice(
            provider.mgmt.list_image_openshift())['name'])
    # image endpoint
    image_endpoint = 'https://' + provider.hostname + \
        ':8443/oapi/v1/images/' + image_name

    template_name = str(random.choice(provider.mgmt.list_template())[0])
    template_name_in_project = [
        x.project_name for x in provider.mgmt.list_template() if x[0] == template_name][0]
    # template endpoint
    template_endpoint = 'https://' + provider.hostname + ':8443/oapi/v1/namespaces/' + \
        template_name_in_project + '/templates/' + template_name

    object_names.extend([project_name,
                         service_name,
                         rc_name,
                         pod_name,
                         node_name,
                         image_name,
                         template_name])

    obj_endpoints.extend([project_endpoint,
                          service_endpoint,
                          rc_endpoint,
                          pod_endpoint,
                          node_endpoint,
                          image_endpoint,
                          template_endpoint])

    json_new_payload = []

    # use different label for each object and generate json
    for obj_name in objects_ocp:
        key_label = fauxfactory.gen_alphanumeric(6)
        value_label = fauxfactory.gen_alphanumeric(6)
        json_payload_format = '{"apiVersion":"v1","kind":' + obj_name + \
                              ',"metadata":{"labels":{' + '"%s"' % key_label + ':' \
                              + '"%s"' % value_label + '}}}'
        json_new_payload.append(json_payload_format)

    # create lists of keys and values from newly generated labels for each
    # object

    project = (json.loads(json_new_payload[0])).values()[2]
    project_key_value = str(project.values()[0])
    project_kv_list = re.findall(r"'(\w+)'", project_key_value)

    service = (json.loads(json_new_payload[1])).values()[2]
    service_key_value = str(service.values()[0])
    service_kv_list = re.findall(r"'(\w+)'", service_key_value)

    rc = (json.loads(json_new_payload[2])).values()[2]
    rc_key_value = str(rc.values()[0])
    rc_kv_list = re.findall(r"'(\w+)'", rc_key_value)

    pod = (json.loads(json_new_payload[3])).values()[2]
    pod_key_value = str(pod.values()[0])
    pod_kv_list = re.findall(r"'(\w+)'", pod_key_value)

    node = (json.loads(json_new_payload[4])).values()[2]
    node_key_value = str(node.values()[0])
    node_kv_list = re.findall(r"'(\w+)'", node_key_value)

    image = (json.loads(json_new_payload[5])).values()[2]
    image_key_value = str(image.values()[0])
    image_kv_list = re.findall(r"'(\w+)'", image_key_value)

    template = (json.loads(json_new_payload[6])).values()[2]
    template_key_value = str(template.values()[0])
    template_kv_list = re.findall(r"'(\w+)'", template_key_value)

    # extracted list of keys
    obj_keys_list.extend([project_kv_list[0],
                          service_kv_list[0],
                          rc_kv_list[0],
                          pod_kv_list[0],
                          node_kv_list[0],
                          image_kv_list[0],
                          template_kv_list[0]])

    # extracted list of values
    obj_values_list.extend([project_kv_list[1],
                            service_kv_list[1],
                            rc_kv_list[1],
                            pod_kv_list[1],
                            node_kv_list[1],
                            image_kv_list[1],
                            template_kv_list[1]])

    return json_new_payload, object_names, obj_endpoints, obj_keys_list, obj_values_list


@pytest.mark.polarion('CMP-10572')
def test_labels(provider, soft_assert):

    json_api_payload, obj_api_names, obj_api_endpoints, obj_api_keys, obj_api_values \
        = create_api_data(provider)

    headers = {'Authorization': 'Bearer' + ' ' + provider.mgmt.auth,
               'Content-Type': 'application/strategic-merge-patch+json'}

    # execute the PATCH request and check the status
    create_label_project = requests.patch(
        obj_api_endpoints[0],
        headers=headers,
        verify=False,
        data=json_api_payload[0])
    assert create_label_project.status_code == 200

    create_label_service = requests.patch(
        obj_api_endpoints[1],
        headers=headers,
        verify=False,
        data=json_api_payload[1])
    assert create_label_service.status_code == 200

    create_label_rc = requests.patch(
        obj_api_endpoints[2],
        headers=headers,
        verify=False,
        data=json_api_payload[2])
    assert create_label_rc.status_code == 200

    create_label_pod = requests.patch(
        obj_api_endpoints[3],
        headers=headers,
        verify=False,
        data=json_api_payload[3])
    assert create_label_pod.status_code == 200

    create_label_node = requests.patch(
        obj_api_endpoints[4],
        headers=headers,
        verify=False,
        data=json_api_payload[4])
    assert create_label_node.status_code == 200

    create_label_image = requests.patch(
        obj_api_endpoints[5],
        headers=headers,
        verify=False,
        data=json_api_payload[5])
    assert create_label_image.status_code == 200

    create_label_template = requests.patch(
        obj_api_endpoints[6],
        headers=headers,
        verify=False,
        data=json_api_payload[6])
    assert create_label_template.status_code == 200

    # verify the labels in CFME

    navigate_to(provider, 'Details')
    tb.select(
        'Configuration',
        'Refresh items and relationships',
        invokes_alert=True)
    sel.handle_alert()

    tb.select('Reload Current Display')
    time.sleep(120)

    for test_obj in TEST_OBJECTS:
        navigate_to(test_obj, 'All')

        if test_obj is Project:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            project_ui = [r.name.text for r in list_tbl.rows(
            ) if r.name.text == obj_api_names[0]]
            for name in project_ui:
                obj = Project(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[0]
                label_value = obj_api_values[0]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Service:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            service_ui = [r.name.text for r in list_tbl.rows(
            ) if r.name.text == obj_api_names[1]]
            for name in service_ui:
                obj = Service(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[1]
                label_value = obj_api_values[1]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Replicator:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            rc_ui = [r.name.text for r in list_tbl.rows() if r.name.text ==
                     obj_api_names[2]]
            for name in rc_ui:
                obj = Replicator(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[2]
                label_value = obj_api_values[2]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Pod:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            pod_ui = [r.name.text for r in list_tbl.rows(
            ) if r.name.text == obj_api_names[3]]
            for name in pod_ui:
                obj = Pod(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[3]
                label_value = obj_api_values[3]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Node:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            node_ui = [r.name.text for r in list_tbl.rows(
            ) if r.name.text == obj_api_names[4]]
            for name in node_ui:
                obj = Node(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[4]
                label_value = obj_api_values[4]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Image:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            image_ui = [r for r in list_tbl.rows() if obj_api_names[
                5] in str(r.id.text)]
            for img in image_ui:
                # tag = 'tr'
                obj = Image(img.name.text, img.tag.text, provider)
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[5]
                label_value = obj_api_values[5]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")

        if test_obj is Template:
            tb.select("List View")
            list_tbl = CheckboxTable(
                table_locator="//div[@id='list_grid']//table")
            template_ui = [
                r.name.text for r in list_tbl.rows() if r.name.text == obj_api_names[6]]
            for name in template_ui:
                obj = Template(name, provider)
                obj.summary.reload()
                ui_labels = obj.summary.labels.items()
                label_key = obj_api_keys[6]
                label_value = obj_api_values[6]
                if label_key in ui_labels:
                    soft_assert(
                        label_value == ui_labels[label_key],
                        "No label found")
