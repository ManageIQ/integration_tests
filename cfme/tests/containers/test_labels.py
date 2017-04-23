import pytest

from cfme.fixtures import pytest_selenium as sel
import requests
from cfme.containers.pod import Pod
from cfme.containers.service import Service
from cfme.containers.node import NodeCollection
from cfme.containers.replicator import Replicator
from cfme.containers.route import Route
from cfme.containers.image import Image
from cfme.containers.template import Template
from cfme.containers.project import Project
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from utils import testgen, version


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


TEST_OBJECTS = [Pod, Service, Replicator, Project, NodeCollection, Template, Route, Image]


def check_labels(test_obj, list_ui, provider, soft_assert):
    for name in list_ui:
        obj = test_obj(name, provider)
        obj.summary.reload()
        redhat = obj.summary.labels.redhat.text_value

        soft_assert(
            redhat == 'essential',
            'Expected value for redhat label is "essential", got {} instead'.format(redhat))


@pytest.mark.polarion('CMP-10572')
def test_labels(provider, soft_assert):
    """ This test creates a new label for nodes, pods, replicators,
        services, images, routes and projects using Openshift API.
        Then we verify the newly created label in CFME.The label
        that is being used is redhat=essential.

    """

    headers = {'Authorization': 'Bearer' + ' ' + provider.mgmt.auth, 'Content-Type':
               'application/strategic-merge-patch+json'}
    headers_route = {'Authorization': 'Bearer' + ' ' + provider.mgmt.auth,
                     'Content-Type': 'application/json'}

    url = 'https://' + provider.hostname + ':8443/api/v1/namespaces/default'
    url_openshift = 'https://' + provider.hostname + ':8443/oapi/v1/namespaces/default'

    pod_name = str([x for y in list(provider.mgmt.list_container_group()) for x in y][0])
    service_name = str([x for y in list(provider.mgmt.list_service()) for x in y][0])
    rc_name = str([x for y in list(provider.mgmt.list_replication_controller()) for x in y][0])
    template_name = str([x for y in list(provider.mgmt.list_template()) for x in y][0])
    image_name = 'sha256:ae500c8640bb43a6e028ccb81248deee0c2e36063d725c0d411d9a08f379b868'

    # create a new route, it will be tested separately

    url_route_new = url_openshift + '/routes'
    json_label_route = '{"apiVersion":"v1","kind":"Route","metadata":{"name":"route-tester-one,' \
                       '"namespace":"default","labels":{"redhat":"essential"}},' \
                       '"spec":{"to":{"kind":"Service",' \
                       '"name":"route-tester-one"}}}'
    requests.post(url_route_new, headers=headers_route, verify=False, data=json_label_route)

    # object list

    obj_list = ('/pods/', '/services/', '/replicationcontrollers/',
                '/project/', '/node/', '/template/', '/image/')

    for _ in obj_list:
        if obj_list[0] in obj_list:
            url_obj = url + obj_list[0] + pod_name
            json_data = '{"apiVersion":"v1","kind":"Pod","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        elif obj_list[1] in obj_list:
            url_obj = url + obj_list[1] + service_name
            json_data = '{"apiVersion":"v1","kind":"Service","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        elif obj_list[2] in obj_list:
            url_obj = url + obj_list[2] + rc_name
            json_data = '{"apiVersion":"v1","kind":"ReplicationController","metadata":{' \
                        '"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        elif obj_list[3] in obj_list:
            url_obj = 'https://' + provider.hostname + \
                      ':8443/api/v1/namespaces/openshift-infra'
            json_data = '{"apiVersion":"v1","kind":"Namespace","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        elif obj_list[4] in obj_list:
            url_obj = 'https://' + provider.hostname + ':8443/api/v1/nodes/' + provider.hostname
            json_data = '{"apiVersion":"v1","kind":"Node","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        elif obj_list[5] in obj_list:
            url_obj = 'https://' + provider.hostname + \
                      ':8443/oapi/v1/namespaces/openshift/templates/' + template_name
            json_data = '{"apiVersion":"v1","kind":"Template","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)
        else:
            url_obj = 'https://' + provider.hostname + \
                      ':8443/oapi/v1/images/' + image_name
            json_data = '{"apiVersion":"v1","kind":"Image","metadata":' \
                        '{"labels":{"redhat":"essential"}}}'
            requests.patch(url_obj, headers=headers, verify=False, data=json_data)

    # verify the labels in CFME

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
    pod_default_names_api = [i for i in pod_default_api if i == pod_name]

    rc_list_api = provider.mgmt.list_replication_controller()
    rc_default_api = [rc for rc in rc_list_api if rc.project_name == 'default']
    rc_default_names_api = [i for i in rc_default_api if i == rc_name]

    service_list_api = provider.mgmt.list_service()
    service_default_api = [
        service for service in service_list_api if service.project_name == 'default']
    service_default_names_api = [i for i in service_default_api if i == service_name]

    node_default_api = provider.mgmt.list_node()
    node_default_names_api = [i[0] for i in node_default_api]

    template_list_api = provider.mgmt.list_template()
    template_default_api = [template for template in template_list_api]
    template_default_names_api = [i for i in template_default_api if i == template_name]

    for test_obj in TEST_OBJECTS:
        navigate_to(test_obj, 'All')

        list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

        if test_obj is Pod:
            tb.select("List View")
            pod_ui = [r.name.text for r in list_tbl.rows()]
            pod_selected_ui = [x for x in pod_ui if x in pod_default_names_api]
            check_labels(test_obj, pod_selected_ui, provider, soft_assert)

        elif test_obj is Replicator:
            tb.select("List View")
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

        elif test_obj is Service:
            tb.select("List View")
            service_ui = [r.name.text for r in list_tbl.rows()]
            service_selected_ui = [x for x in service_ui if x in service_default_names_api]
            check_labels(test_obj, service_selected_ui, provider, soft_assert)

        elif test_obj is Template:
            tb.select("List View")
            template_ui = [r.name.text for r in list_tbl.rows()]
            template_selected_ui = [x for x in template_ui if x in template_default_names_api]
            check_labels(test_obj, template_selected_ui, provider, soft_assert)

        elif test_obj is Route:
            tb.select("List View")
            route_ui = [r.name.text for r in list_tbl.rows()]
            route_selected_ui = filter(lambda ch: 'route-tester-one' in ch, route_ui)
            check_labels(test_obj, route_selected_ui, provider, soft_assert)

        elif test_obj is Project:
            tb.select("List View")
            project_ui = [r.name.text for r in list_tbl.rows()]
            project_selected_ui = filter(lambda ch: 'openshift-infra' in ch, project_ui)
            check_labels(test_obj, project_selected_ui, provider, soft_assert)

        else:
            tb.select("List View")
            image_ui = [r.name.text for r in list_tbl.rows()]
            image_selected_ui = filter(lambda ch: 'dotnet/dotnetcore-10-rhel7 ' in ch, image_ui)
            for name in image_selected_ui:
                tag = ''
                obj = Image(name, tag, provider)
                obj.summary.reload()
                redhat = obj.summary.labels.redhat.text_value
                soft_assert(
                    redhat == 'essential',
                    'Expected value for redhat label is "essential", got {} instead'.format(redhat))
