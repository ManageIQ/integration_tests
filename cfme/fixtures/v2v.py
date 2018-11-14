import fauxfactory
import itertools
import pytest
import json
from collections import namedtuple
from riggerlib import recursive_update
from widgetastic.utils import partial_match

from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger


FormDataVmObj = namedtuple(
    'FormDataVmObj', ['form_data', 'vm_list']
)


@pytest.fixture(scope='function')
def v2v_providers(request, second_provider, provider):
    """ Fixture to setup providers """
    V2vProviders = namedtuple(
        'V2vProviders', ['vmware_provider', 'rhv_provider']
    )
    vmware_provider, rhv_provider = None, None
    for provider in [second_provider, provider]:
        if provider.one_of(VMwareProvider):
            vmware_provider = provider
        elif provider.one_of(RHEVMProvider):
            rhv_provider = provider
        else:
            pytest.skip("Provider {} is not a valid provider for v2v tests".
                format(provider.name))
    v2v_providers = V2vProviders(vmware_provider=vmware_provider, rhv_provider=rhv_provider)
    setup_or_skip(request, v2v_providers.vmware_provider)
    setup_or_skip(request, v2v_providers.rhv_provider)
    yield v2v_providers
    v2v_providers.vmware_provider.delete_if_exists(cancel=False)
    v2v_providers.rhv_provider.delete_if_exists(cancel=False)


@pytest.fixture(scope='function')
def host_creds(request, v2v_providers):
    """Add credentials to VMware and RHV hosts."""
    if len(v2v_providers) > 2:
        pytest.skip("There are more than two providers in v2v_providers fixture,"
                    "which is invalid, skipping.")
    try:
        vmware_provider = v2v_providers.vmware_provider
        rhv_provider = v2v_providers.rhv_provider
        vmware_hosts = vmware_provider.hosts.all()
        for host in vmware_hosts:
            host_data, = [data for data in vmware_provider.data['hosts']
                          if data['name'] == host.name]
            host.update_credentials_rest(credentials=host_data['credentials'])

        rhv_hosts = rhv_provider.hosts.all()
        rhv_hosts = rhv_hosts if getattr(request, 'param', '') == 'multi-host' else rhv_hosts[0:1]
        for host in rhv_hosts:
            host_data, = [data for data in rhv_provider.data['hosts'] if data['name'] == host.name]
            host.update_credentials_rest(credentials=host_data['credentials'])
    except Exception:
        # if above throws ValueError or TypeError or other exception, just skip the test
        logger.exception("Exception when trying to add the host credentials.")
        pytest.skip("No data for hosts in providers, failed to retrieve hosts and add creds.")
    # only yield RHV hosts as they will be required to tag with conversion_tags fixture
    yield rhv_hosts
    for host in itertools.chain(rhv_hosts, vmware_hosts):
        host.remove_credentials_rest()


def _tag_cleanup(host_obj, tag1, tag2):
    """
        Clean Up Tags

        Returns: Boolean True if all Tags were removed/cleaned
        or False means all required Tags are present on host.
    """
    def extract_tag(tag):
        # Following strip will remove extra asterisk from tag assignment
        return tag.category.display_name.strip(" *"), tag.display_name

    valid_tags = {extract_tag(tag1), extract_tag(tag2)}
    tags = host_obj.get_tags()
    tags_set = set(map(extract_tag, tags))
    # we always neeed 2 tags for migration, if total is less than 2
    # don't bother checking what tag was it, just remove it and
    # then add all required tags via add_tags() call. or if tags on host
    # are not subset of valid tags, we still remove them.
    if len(tags_set) < 2 or not tags_set.issubset(valid_tags):
        host_obj.remove_tags(tags=tags)
        return True
    return False


@pytest.fixture(scope='function')
def conversion_tags(request, appliance, host_creds):
    """Assigning tags to conversation host"""
    tag1 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Host *').collections.tags.instantiate(
        display_name='t')
    if hasattr(request, 'param') and request.param == 'SSH':
            transformation_method = 'SSH'
    else:
        transformation_method = 'VDDK'
    tag2 = appliance.collections.categories.instantiate(
        display_name='V2V - Transformation Method').collections.tags.instantiate(
        display_name=transformation_method)
    for host in host_creds:
        # if _tag_cleanup() returns True, means all tags were removed
        if _tag_cleanup(host, tag1, tag2):
            # so we call add_tags to add only required tags
            host.add_tags(tags=(tag1, tag2))
            # set conversion host via rails console
            if appliance.version >= '5.10':
                if isinstance(host.provider, RHEVMProvider):
                    resource_type = 'Host'
                else:
                    resource_type = 'VmOrTemplate'
                appliance.ssh_client.run_rails_command("\'r = Host.find_by(name:{host});\
                c_host = ConversionHost.create(name:{host},resource_id:r.id,resource_type:{type});\
                c_host.{method}_transport_supported = true;\
                c_host.save\'".format(host=json.dumps(host.name),
                                      type=json.dumps(resource_type),
                                      method=transformation_method.lower()))
    yield
    for host in host_creds:
        host.remove_tags(tags=(tag1, tag2))


def get_vm(request, appliance, second_provider, template, datastore='nfs'):
    source_datastores_list = second_provider.data.get('datastores', [])
    source_datastore = [d.name for d in source_datastores_list if d.type == datastore][0]
    collection = second_provider.appliance.provider_based_collection(second_provider)
    vm_name = random_vm_name('v2v-auto')
    vm_obj = collection.instantiate(vm_name,
                                    second_provider,
                                    template_name=template(second_provider)['name'])
    power_on_vm = True
    if template.__name__ == 'win10_template':
        # Need to leave this off, otherwise migration fails
        # because when migration process tries to power off the VM if it is powered off
        # and for win10, it hibernates and that state of filesystem is unsupported
        power_on_vm = False
    vm_obj.create_on_provider(timeout=2400, find_in_cfme=True, allow_skip="default",
                              datastore=source_datastore, power_on=power_on_vm)
    request.addfinalizer(lambda: vm_obj.cleanup_on_provider())
    return vm_obj


def _form_data(second_provider, provider):
    form_data = {
        'general': {
            'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
            'description': "Single Datastore migration of VM from {ds_type1} to"
                           " {ds_type2}".format(ds_type1='nfs', ds_type2='nfs')
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
    vm_list = []
    for template_name in request.param[2]:
        vm_list.append(get_vm(request, appliance, second_provider, template_name))
    return FormDataVmObj(form_data=form_data, vm_list=vm_list)


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
    return FormDataVmObj(form_data=form_data, vm_list=[vm_obj1, vm_obj2])


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
        'network': {
            'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                'mappings': [_form_data_mapping('vlans', second_provider, provider,
                                                request.param[0][0], request.param[0][1]),
                            _form_data_mapping('vlans', second_provider, provider,
                                request.param[1][0], request.param[1][1])]
            }
        }
    })
    vm_obj = get_vm(request, appliance, second_provider, request.param[2])
    return FormDataVmObj(form_data=form_data, vm_list=[vm_obj])


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
    return FormDataVmObj(form_data=form_data, vm_list=[vm_obj])


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
    return FormDataVmObj(form_data=form_data, vm_list=[vm_obj])


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
