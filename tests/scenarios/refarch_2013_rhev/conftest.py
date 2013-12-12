import pytest


@pytest.fixture(params=['rhevm32'])
def provider(request, cfme_data):
    '''Returns management system data from cfme_data'''
    param = request.param
    return cfme_data['management_systems'][param]


@pytest.fixture(params=['qeblade29'])
def host(request, cfme_data):
    '''Returns host data from cfme_data'''
    param = request.param
    return cfme_data['management_systems']['rhevm32']['hosts'][param]


@pytest.fixture(params=['iscsi'])
def datastore(request, cfme_data):
    '''Returns datastore data from cfme_data'''
    param = request.param
    return cfme_data['management_systems']['rhevm32']['datastores'][param]


@pytest.fixture(params=['iscsi'])
def cluster(request, cfme_data):
    '''Returns cluster data from cfme_data'''
    param = request.param
    return cfme_data['management_systems']['rhevm32']['clusters'][param]


@pytest.fixture(scope="module",
                params=["rhel"])
def pxe_server(request, cfme_data):
    '''Returns pxe server data from cfme_data'''
    param = request.param
    return cfme_data['pxe']['pxe_servers'][param]


@pytest.fixture(scope="module")
def pxe_image_names(cfme_data):
    '''Returns pxe image names from cfme_data'''
    return cfme_data['pxe']['images']


@pytest.fixture(scope="module")
def pxe_datastore_names(cfme_data):
    '''Returns pxe datastore names from cfme_data'''
    return cfme_data['pxe']['datastores']


@pytest.fixture(scope="module",
                params=["rhel"])
def pxe_templates(request, cfme_data):
    '''Returns pxe templates from cfme_data'''
    param = request.param
    return cfme_data['pxe']['templates'][param]


@pytest.fixture(scope="module",
                params=["rhel"])
def pxe_template_type(request, cfme_data):
    '''Returns pxe template type from cfme_data'''
    param = request.param
    return cfme_data["pxe"]["templates"][param]["template_type"]


@pytest.fixture(scope="module",
                params=["refarch_zone"])
def zone(request, cfme_data):
    '''Returns appliance zone from cfme_data'''
    param = request.param
    return cfme_data['zones'][param]


@pytest.fixture(params=['rhevm32'])
def appliance(request, cfme_data):
    '''Returns appliance data from cfme_data'''
    param = request.param
    return cfme_data['management_systems'][param]['appliance']


@pytest.fixture(params=['linux_template_workflow'])
def provision(request, cfme_data):
    '''Returns provisioning data from cfme_data'''
    param = request.param
    return cfme_data['provisioning'][param]


@pytest.fixture(scope="module",
                params=["default"])
def roles(request, cfme_data):
    '''Returns server roles from cfme_data'''
    param = request.param
    return cfme_data['server_roles'][param]


@pytest.fixture(scope="module",
                params=["dev", "test"])
def user_group(request, cfme_data):
    '''Returns user groups from cfme_data'''
    param = request.param
    return cfme_data['user_groups'][param]
