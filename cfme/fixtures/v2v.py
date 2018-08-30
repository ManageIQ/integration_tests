import fauxfactory
import pytest
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.fixtures.provider import setup_or_skip
from cfme.utils.generators import random_vm_name


@pytest.fixture(scope='function')
def v2v_providers(request, second_provider, provider):
    """ Fixture to setup providers """
    setup_or_skip(request, second_provider)
    setup_or_skip(request, provider)
    yield second_provider, provider
    second_provider.delete_if_exists(cancel=False)
    provider.delete_if_exists(cancel=False)


@pytest.fixture(scope='function')
def host_creds(v2v_providers):
    """Add credentials to conversation host"""
    provider = v2v_providers[1]
    host = provider.hosts.all()[0]
    host_data = [data for data in provider.data['hosts'] if data['name'] == host.name]
    host.update_credentials_rest(credentials=host_data[0]['credentials'])
    yield host
    host.remove_credentials_rest()


def _tag_cleanup(host_obj, tag1, tag2):
    """
        Clean Up Tags

        Returns: Boolean True or False
    """
    def extract_tag(tag):
        # Following strip will remove extra asterisk from tag assignment
        return tag.category.display_name.strip(" *"), tag.display_name

    valid_tags = {extract_tag(tag1), extract_tag(tag2)}
    tags = host_obj.get_tags()
    tags_set = set(map(extract_tag, tags))

    if len(tags_set) < 2 or not tags_set.issubset(valid_tags):
        host_obj.remove_tags(tags=tags)
        return True
    return False


@pytest.fixture(scope='function')
def conversion_tags(appliance, host_creds):
    """Assigning tags to conversation host"""
    tag1 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Host *').collections.tags.instantiate(
        display_name='t')
    tag2 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Method').collections.tags.instantiate(
        display_name='VDDK')
    if _tag_cleanup(host_creds, tag1, tag2):
        host_creds.add_tags(tags=(tag1, tag2))
    yield
    host_creds.remove_tags(tags=(tag1, tag2))


def get_vm(request, appliance, second_provider, template, datastore='nfs'):
    source_datastores_list = second_provider.data.get('datastores', [])
    source_datastore = [d.name for d in source_datastores_list if d.type == datastore][0]
    collection = second_provider.appliance.provider_based_collection(second_provider)
    vm_name = random_vm_name('v2v-auto')
    vm_obj = collection.instantiate(vm_name,
                                    second_provider,
                                    template_name=template(second_provider)['name'])

    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default",
                              datastore=source_datastore)
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    return vm_obj


def _form_data(second_provider, provider):
    form_data = {
        'general': {
            'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
            'description': "Single Datastore migration of VM from {ds_type1} to"
                           " {ds_type2},".format(ds_type1='nfs', ds_type2='nfs')
        },
        'cluster': {
            'mappings': [_form_data_mapping('clusters', second_provider, provider)]
        },
        'datastore': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('datastores', second_provider, provider,
                                                'nfs', 'nfs')]
            }
        },
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                'VM Network', 'ovirtmgmt')]
            }
        }
    }
    return form_data


@pytest.fixture(scope='function')
def form_data_multiple_vm_obj_single_datastore(request, appliance, second_provider, provider):
    # this fixture will take list of N VM templates via request and call get_vm for each
    cluster = provider.data.get('clusters', [False])[0]
    if not cluster:
        pytest.skip("No data for cluster available on provider.")

    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Single Datastore migration of VM from {ds_type1} to"
            " {ds_type2},".format(ds_type1=request.param[0], ds_type2=request.param[1])},
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                'VM Network', 'ovirtmgmt')]
            }
        }
    })
    vm_obj = []
    for template_name in request.param[2]:
        vm_obj.append(get_vm(request, appliance, second_provider, template_name))
    return form_data, vm_obj


@pytest.fixture(scope='function')
def form_data_single_datastore(request, second_provider, provider):
    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Single Datastore migration of VM from {ds_type1} to"
                           " {ds_type2},".format(ds_type1=request.param[0],
                                                 ds_type2=request.param[1])
        },
        'datastore': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('datastores', second_provider, provider,
                                                request.param[0], request.param[1])]
            }
        }
    })
    return form_data


@pytest.fixture(scope='function')
def form_data_single_network(request, second_provider, provider):
    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Single Network migration of VM from {vlan1} to {vlan2},".
                     format(vlan1=request.param[0], vlan2=request.param[1])},
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                request.param[0], request.param[1])]
            }
        }
    })
    return form_data


@pytest.fixture(scope='function')
def form_data_dual_vm_obj_dual_datastore(request, appliance, second_provider, provider):
    vmware_nw = second_provider.data.get('vlans', [None])[0]
    rhvm_nw = provider.data.get('vlans', [None])[0]
    cluster = provider.data.get('clusters', [False])[0]
    if not vmware_nw or not rhvm_nw or not cluster:
        pytest.skip("No data for source or target network in providers.")

    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Dual Datastore migration of VM from {} to {},& from {} to {}"
                     .format(request.param[0][0], request.param[0][1], request.param[1][0],
                             request.param[1][1])},
        'datastore': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('datastores', second_provider, provider,
                                                request.param[0][0], request.param[0][1]),
                             _form_data_mapping('datastores', second_provider, provider,
                                                request.param[1][0], request.param[1][1])]
            }
        },
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                second_provider.data.get('vlans')[0],
                                                provider.data.get('vlans')[0])]
            }
        }
    })
    # creating 2 VMs on two different datastores and returning its object list
    vm_obj1 = get_vm(request, appliance, second_provider, request.param[0][2], request.param[0][0])
    vm_obj2 = get_vm(request, appliance, second_provider, request.param[1][2], request.param[1][0])
    return form_data, [vm_obj1, vm_obj2]


@pytest.fixture(scope='function')
def form_data_vm_obj_dual_nics(request, appliance, second_provider, provider):
    vmware_nw = second_provider.data.get('vlans', [None])[0]
    rhvm_nw = provider.data.get('vlans', [None])[0]
    cluster = provider.data.get('clusters', [False])[0]
    if not vmware_nw or not rhvm_nw or not cluster:
        pytest.skip("No data for source or target network in providers.")

    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Dual Datastore migration of VM from {} to {},& from {} to {}"
                     .format(request.param[0][0], request.param[0][1], request.param[1][0],
                             request.param[1][1])},
        'datastore': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('datastores', second_provider, provider,
                                                request.param[0][0], request.param[0][1]),
                             _form_data_mapping('datastores', second_provider, provider,
                                                request.param[1][0], request.param[1][1])]
            }
        },
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                second_provider.data.get('vlans')[0],
                                                provider.data.get('vlans')[0])]
            }
        }
    })
    vm_obj = get_vm(request, appliance, second_provider, request.param[2])
    return form_data, [vm_obj]


@pytest.fixture(scope='function')
def form_data_vm_obj_single_datastore(request, appliance, second_provider, provider):
    """Return Infra Mapping form data and vm object"""
    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Single Datastore migration of VM from {ds_type1} to {ds_type2},"
                     .format(ds_type1=request.param[0], ds_type2=request.param[1])},
        'datastore': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('datastores', second_provider, provider,
                                                request.param[0], request.param[1])]
            }
        }
    })
    vm_obj = get_vm(request, appliance, second_provider, request.param[2], request.param[0])
    return form_data, [vm_obj]


@pytest.fixture(scope='function')
def form_data_vm_obj_single_network(request, appliance, second_provider, provider):
    form_data = _form_data(second_provider, provider)
    recursive_update(form_data, {
        'general': {
            'description': "Single Network migration of VM from {vlan1} to {vlan2},".
                     format(vlan1=request.param[0], vlan2=request.param[1])},
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                request.param[0], request.param[1])]
            }
        }
    })
    vm_obj = get_vm(request, appliance, second_provider, request.param[2])
    return form_data, [vm_obj]


def _form_data_mapping(selector, second_provider, provider, source_list=None, target_list=None):
    source_data = second_provider.data.get(selector, [])
    target_data = provider.data.get(selector, [])
    if selector is 'clusters':
        source = source_data if source_data else None
        target = target_data if target_data else None
        skip_test = not source or not target
    else:
        if selector is 'datastores':
            source = [d.name for d in source_data if d.type == source_list]
            target = [d.name for d in target_data if d.type == target_list]
        else:
            source = [v for v in source_data if v == source_list]
            target = [v for v in target_data if v == target_list]
        skip_test = not (source_data and target_data and source and target)

    if skip_test:
        pytest.skip("No data for source or target {} in providers.".format(selector))
    else:
        _source, _target = partial_match(source[0]), partial_match(target[0])

    return {
        'sources': [_source],
        'target': [_target]
    }
