"""Test to validate basic navigations.Later to be replaced with End-to-End functional testing."""
import fauxfactory
import pytest

from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import partial_match

from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.appliance.implementations.ui import navigate_to, navigator
from cfme.utils.generators import random_vm_name
from cfme.utils.log import logger
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.provider(
        classes=[RHEVMProvider],
        selector=ONE_PER_VERSION
    ),
    pytest.mark.provider(
        classes=[VMwareProvider],
        selector=ONE_PER_VERSION,
        fixture_name='second_provider'
    )
]


def _form_data_cluster_mapping(second_provider, provider):
    # since we have only one cluster on providers
    source_cluster = second_provider.data.get('clusters')[0]
    target_cluster = provider.data.get('clusters')[0]

    if not source_cluster or not target_cluster:
        pytest.skip("No data for source or target cluster in providers.")

    return {
        'sources': [partial_match(source_cluster)],
        'target': [partial_match(target_cluster)]
    }


def _form_data_datastore_mapping(second_provider, provider, source_type, target_type):
    source_datastores_list = second_provider.data.get('datastores')
    target_datastores_list = provider.data.get('datastores')

    if not source_datastores_list or not target_datastores_list:
        pytest.skip("No data for source or target cluster in providers.")

    # assuming, we just have 1 datastore of each type
    source_datastore = [d.name for d in source_datastores_list if d.type == source_type][0]
    target_datastore = [d.name for d in target_datastores_list if d.type == target_type][0]

    return {
        'sources': [partial_match(source_datastore)],
        'target': [partial_match(target_datastore)]
    }


def _form_data_network_mapping(second_provider, provider, source_network_name, target_network_name):
    source_vlans_list = second_provider.data.get('vlans')
    target_vlans_list = provider.data.get('vlans')

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
def form_data_single_datastore(request, second_provider, provider):
    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Single Datastore migration of VM from {ds_type1} to"
                " {ds_type2},".format(ds_type1=request.param[0], ds_type2=request.param[1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(second_provider, provider)]
            },
            'datastore': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(second_provider, provider,
                        request.param[0], request.param[1])]
                }
            },
            'network': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(second_provider, provider,
                        'VM Network', 'ovirtmgmt')]
                }
            }
        })
    return form_data


@pytest.fixture(scope='function')
def form_data_single_network(request, second_provider, provider):
    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Single Network migration of VM from {vlan1} to {vlan2},".
                format(vlan1=request.param[0], vlan2=request.param[1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(second_provider, provider)]
            },
            'datastore': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(second_provider, provider,
                        'nfs', 'nfs')]
                }
            },
            'network': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(second_provider, provider,
                        request.param[0], request.param[1])]
                }
            }
        })
    return form_data


@pytest.fixture(scope='function')
def form_data_dual_datastore(request, second_provider, provider):
    vmware_nw = second_provider.data.get('vlans')[0]
    rhvm_nw = provider.data.get('vlans')[0]

    if not vmware_nw or not rhvm_nw:
        pytest.skip("No data for source or target network in providers.")

    form_data = (
        {
            'general': {
                'name': 'infra_map_{}'.format(fauxfactory.gen_alphanumeric()),
                'description': "Dual Datastore migration of VM from {} to {},"
                "& from {} to {}".
                format(request.param[0][0], request.param[0][1], request.param[1][0],
                    request.param[1][1])
            },
            'cluster': {
                'mappings': [_form_data_cluster_mapping(second_provider, provider)]
            },
            'datastore': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_datastore_mapping(second_provider, provider,
                            request.param[0][0], request.param[0][1]),
                        _form_data_datastore_mapping(second_provider, provider,
                            request.param[1][0], request.param[1][1])
                    ]
                }
            },
            'network': {
                'Cluster ({})'.format(provider.data.get('clusters')[0]): {
                    'mappings': [_form_data_network_mapping(second_provider, provider,
                        second_provider.data.get('vlans')[0], provider.data.get('vlans')[0])]
                }
            }
        })
    return form_data


vms = []


@pytest.fixture(scope="module")
def vm_list(request, appliance, second_provider, provider):
    """Fixture to provide list of vm objects"""
    # TODO: Need to add list of vm and its configuration in cfme_data.yaml
    templates = [second_provider.data.templates.big_template['name']]
    for template in templates:
        vm_name = random_vm_name(context='v2v-auto')
        collection = appliance.provider_based_collection(second_provider)
        vm = collection.instantiate(vm_name, second_provider, template_name=template)

        if not second_provider.mgmt.does_vm_exist(vm_name):
            logger.info("deploying {} on provider {}".format(vm_name, second_provider.key))
            vm.create_on_provider(allow_skip="default", datastore=request.param)
            vms.append(vm)
    return vms


@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs'],
                            ['nfs', 'iscsi'], ['iscsi', 'iscsi']], indirect=True)
def test_single_datastore_single_vm_mapping_crud(appliance, form_data_single_datastore, providers,
                                                 conversion_tags, soft_assert):
    # TODO: This test case does not support update
    # as update is not a supported feature for mapping.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()
    mapping_list = view.infra_mapping_list
    mapping_list.delete_mapping(mapping.name)
    view.browser.refresh()
    view.wait_displayed()
    try:
        assert mapping.name not in view.infra_mapping_list.read()
    except NoSuchElementException:
        # meaning there was only one mapping that is deleted, list is empty
        pass


@pytest.mark.parametrize('form_data_single_network', [['VM Network', 'ovirtmgmt'],
                            ['DPortGroup', 'ovirtmgmt']], indirect=True)
def test_single_network_single_vm_mapping_crud(appliance, conversion_tags, providers,
                                               form_data_single_network):
    # TODO: This test case does not support update
    # as update is not a supported feature for mapping.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_network)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()
    mapping_list = view.infra_mapping_list
    mapping_list.delete_mapping(mapping.name)
    view.browser.refresh()
    view.wait_displayed()
    try:
        assert mapping.name not in view.infra_mapping_list.read()
    except NoSuchElementException:
        # meaning there was only one mapping that is deleted, list is empty
        pass


@pytest.mark.parametrize('form_data_dual_datastore', [[['nfs', 'nfs'], ['iscsi', 'iscsi']],
                            [['nfs', 'local'], ['iscsi', 'iscsi']]], indirect=True)
def test_dual_datastore_dual_vm_mapping_crud(appliance, form_data_dual_datastore, migration_ui,
                                             providers):
    # TODO: Add "Delete" method call.This test case does not support update/delete
    # as update is not a supported feature for mapping,
    # and delete is not supported in our automation framework.
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_dual_datastore)
    view = navigate_to(infrastructure_mapping_collection, 'All', wait_for_view=True)
    assert mapping.name in view.infra_mapping_list.read()
    mapping_list = view.infra_mapping_list
    mapping_list.delete_mapping(mapping.name)
    view.browser.refresh()
    view.wait_displayed()
    try:
        assert mapping.name not in view.infra_mapping_list.read()
    except NoSuchElementException:
        # meaning there was only one mapping that is deleted, list is empty
        pass


@pytest.mark.parametrize('vm_list', ['NFS_Datastore_1', 'iSCSI_Datastore_1'], ids=['NFS', 'ISCSI'],
                         indirect=True)
@pytest.mark.parametrize('form_data_single_datastore', [['nfs', 'nfs']], indirect=True)
def test_end_to_end_migration(appliance, migration_ui, providers, form_data_single_datastore,
                              vm_list):
    infrastructure_mapping_collection = appliance.collections.v2v_mappings
    mapping = infrastructure_mapping_collection.create(form_data_single_datastore)
    coll = appliance.collections.v2v_plans
    coll.create(name="plan_{}".format(fauxfactory.gen_alphanumeric()),
                description="desc_{}".format(fauxfactory.gen_alphanumeric()),
                infra_map=mapping.name,
                vm_list=vm_list,
                start_migration=True)
    view = appliance.browser.create_view(navigator.get_class(coll, 'All').VIEW)
    # explicit wait for spinner of in-progress status card
    wait_for(lambda: bool(view.progress_bar.is_plan_started(coll.name)),
             message="migration plan is starting, be patient please", delay=5, num_sec=120)
    assert view._get_status(coll.name) == "Completed Plans"


def test_conversion_host_tags(appliance, providers):
    """Tests following cases:

    1)Test Attribute in UI indicating host has/has not been configured as conversion host like Tags
    2)Test converstion host tags
    """
    tag1 = (appliance.collections.categories.instantiate(
            display_name='V2V - Transformation Host *')
            .collections.tags.instantiate(display_name='t'))

    tag2 = (appliance.collections.categories.instantiate(
            display_name='V2V - Transformation Method')
            .collections.tags.instantiate(display_name='VDDK'))

    host = providers[1].hosts[0]
    # Remove any prior tags
    host.remove_tags(host.get_tags())

    host.add_tag(tag1)
    assert host.get_tags()[0].category.display_name in tag1.category.display_name
    host.remove_tag(tag1)

    host.add_tag(tag2)
    assert host.get_tags()[0].category.display_name in tag2.category.display_name
    host.remove_tag(tag2)

    host.remove_tags(host.get_tags())
