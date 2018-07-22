"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from widgetastic.utils import partial_match

from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import testgen
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.ignore_stream('5.8')]


# TODO: Following function is due for refactor as soon as PR#7408 is merged.
def pytest_generate_tests(metafunc):
    """This is parametrizing over the provider types and creating permutations of provider pairs,
       adding ids and argvalues."""
    argnames1, argvalues1, idlist1 = testgen.providers_by_class(metafunc, [VMwareProvider])
    argnames2, argvalues2, idlist2 = testgen.providers_by_class(metafunc, [RHEVMProvider])

    new_idlist = []
    new_argvalues = []
    new_argnames = ['nvc_prov', 'rhvm_prov']

    for index1, argvalue_tuple1 in enumerate(argvalues1):
        for index2, argvalue_tuple2 in enumerate(argvalues2):
            new_idlist.append('{}-{}'.format(idlist1[index1], idlist2[index2]))
            new_argvalues.append((argvalue_tuple1[0], argvalue_tuple2[0]))
    testgen.parametrize(metafunc, new_argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope='module')
def create_provider(request, nvc_prov, rhvm_prov):
    """ Fixture to setup providers """
    setup_or_skip(request, nvc_prov)
    setup_or_skip(request, rhvm_prov)


def _form_data_cluster_mapping(nvc_prov, rhvm_prov):
    # since we have only one cluster on providers
    source_cluster = nvc_prov.data.get('clusters')[0]
    target_cluster = rhvm_prov.data.get('clusters')[0]

    if not source_cluster or not target_cluster:
        pytest.skip("No data for source or target cluster in providers.")

    return {
        'sources': [partial_match(source_cluster)],
        'target': [partial_match(target_cluster)]
    }


def _form_data_datastore_mapping(nvc_prov, rhvm_prov, source_type, target_type):
    source_datastores_list = nvc_prov.data.get('datastores')
    target_datastores_list = rhvm_prov.data.get('datastores')

    if not source_datastores_list or not target_datastores_list:
        pytest.skip("No data for source or target cluster in providers.")

    # assuming, we just have 1 datastore of each type
    source_datastore = [d.name for d in source_datastores_list if d.type == source_type][0]
    target_datastore = [d.name for d in target_datastores_list if d.type == target_type][0]

    return {
        'sources': [partial_match(source_datastore)],
        'target': [partial_match(target_datastore)]
    }


def _form_data_network_mapping(nvc_prov, rhvm_prov, source_network_name, target_network_name):
    source_vlans_list = nvc_prov.data.get('vlans')
    target_vlans_list = rhvm_prov.data.get('vlans')

    if not source_vlans_list or not target_vlans_list:
        pytest.skip("No data for source or target cluster in providers.")

    # assuming there will be only 1 network matching given name
    source_network = [v for v in source_vlans_list if v == source_network_name][0]
    target_network = [v for v in target_vlans_list if v == target_network_name][0]

    return {
        'sources': [partial_match(source_network)],
        'target': [partial_match(target_network)]
    }


@pytest.fixture(scope='function')
def form_data_single_datastore(request, nvc_prov, rhvm_prov):
    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Single Datastore migration  of VM from {ds_type1} to"
                " {ds_type2},".format(ds_type1=request.param[0], ds_type2=request.param[1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(nvc_prov, rhvm_prov)]
            },
            'datastore': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(nvc_prov, rhvm_prov,
                        request.param[0], request.param[1])]
                }
            },
            'network': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(nvc_prov, rhvm_prov,
                        'VM Network', 'ovirtmgmt')]
                }
            }
        })
    return form_data


@pytest.fixture(scope='function')
def form_data_single_network(request, nvc_prov, rhvm_prov):
    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Single Network migration  of VM from {vlan1} to {vlan2},".
                format(vlan1=request.param[0], vlan2=request.param[1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(nvc_prov, rhvm_prov)]
            },
            'datastore': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(nvc_prov, rhvm_prov,
                        'nfs', 'nfs')]
                }
            },
            'network': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(nvc_prov, rhvm_prov,
                        request.param[0], request.param[1])]
                }
            }
        })
    return form_data


@pytest.fixture(scope='function')
def form_data_dual_datastore(request, nvc_prov, rhvm_prov):
    vmware_nw = nvc_prov.data.get('vlans')[0]
    rhvm_nw = rhvm_prov.data.get('vlans')[0]

    if not vmware_nw or not rhvm_nw:
        pytest.skip("No data for source or target network in providers.")

    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Dual Datastore migration  of VM from {} to {},"
                "& from {} to {}".
                format(request.param[0][0], request.param[0][1], request.param[1][0],
                    request.param[1][1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(nvc_prov, rhvm_prov)]
            },
            'datastore': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(nvc_prov, rhvm_prov,
                            request.param[0][0], request.param[0][1]),
                        _form_data_datastore_mapping(nvc_prov, rhvm_prov,
                            request.param[1][0], request.param[1][1])
                    ]
                }
            },
            'network': {
                'Cluster ({})'.format(rhvm_prov.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(nvc_prov, rhvm_prov,
                        nvc_prov.data.get('vlans')[0], rhvm_prov.data.get('vlans')[0])]
                }
            }
        })
    return form_data


@pytest.fixture(scope="module")
def enable_disable_migration_ui(appliance):
    appliance.enable_migration_ui()
    yield
    appliance.disable_migration_ui()


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs'],
                            ['nfs', 'iscsi'], ['iscsi', 'iscsi']], indirect=True)
def test_single_datastore_single_vm_mapping_crud(appliance, enable_disable_migration_ui,
                                            create_provider, form_data_single_datastore):
    # TODO: Add "Delete" method call.This test case does not support update/delete
    # as update is not a supported feature for mapping,
    # and delete is not supported in our automation framework.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()


@pytest.mark.parametrize('form_data_single_network', [['VM Network', 'ovirtmgmt'],
                            ['DPortGroup', 'ovirtmgmt']], indirect=True)
def test_single_network_single_vm_mapping_crud(appliance, enable_disable_migration_ui,
                                            create_provider, form_data_single_network):
    # TODO: Add "Delete" method call.This test case does not support update/delete
    # as update is not a supported feature for mapping,
    # and delete is not supported in our automation framework.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_network)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()


@pytest.mark.parametrize('form_data_dual_datastore', [[['nfs', 'nfs'], ['iscsi', 'iscsi']],
                            [['nfs', 'local'], ['iscsi', 'iscsi']]], indirect=True)
def test_dual_datastore_dual_vm_mapping_crud(appliance, enable_disable_migration_ui,
                                            create_provider, form_data_dual_datastore):
    # TODO: Add "Delete" method call.This test case does not support update/delete
    # as update is not a supported feature for mapping,
    # and delete is not supported in our automation framework.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_dual_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()
