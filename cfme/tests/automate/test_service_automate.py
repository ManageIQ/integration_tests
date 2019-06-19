# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.base.credential import Credential
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.provisioning import do_vm_provisioning
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.blockers import BZ
from cfme.utils.generators import random_vm_name
from cfme.utils.log_validator import LogValidator


pytestmark = [test_requirements.automate]


@pytest.fixture(scope="module")
def new_users(appliance):
    """This fixture creates new users"""
    users = [appliance.collections.users.create(
        name="user_{}".format(fauxfactory.gen_alphanumeric().lower()),
        credential=Credential(principal='uid{}'.format(fauxfactory.gen_alphanumeric(4)),
                              secret=fauxfactory.gen_alphanumeric(4)),
        email=fauxfactory.gen_email(),
        groups=appliance.collections.groups.instantiate(description="EvmGroup-super_administrator"),
        cost_center="Workload",
        value_assign="Database",
    ) for i in range(2)]

    yield users
    for user in users:
        if not BZ(1720273).blocks:
            user.delete_if_exists()
        else:
            user = appliance.rest_api.collections.users.get(name=user.name)
            user.action.delete()


@pytest.fixture(scope='function')
def infra_validate_request(domain):
    # Take the 'ProvisionRequestApproval' class and copy it for own purpose.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Infrastructure"
    ).namespaces.instantiate(name="VM").namespaces.instantiate(
        name="Provisioning").namespaces.instantiate(name="StateMachines").classes.instantiate(
        name="ProvisionRequestApproval").methods.instantiate(
        name="validate_request").copy_to(domain.name)

    method = domain.namespaces.instantiate(
        name="Infrastructure"
    ).namespaces.instantiate(name="VM").namespaces.instantiate(
        name="Provisioning").namespaces.instantiate(name="StateMachines").classes.instantiate(
        name="ProvisionRequestApproval").methods.instantiate(name="validate_request")
    return method


@pytest.fixture(scope='function')
def service_validate_request(domain):
    # Take the 'ProvisionRequestApproval' class and copy it for own purpose.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="Service"
    ).namespaces.instantiate(name="Provisioning").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceProvisionRequestApproval").methods.instantiate(
        name="validate_request").copy_to(domain.name)

    method = domain.namespaces.instantiate(
        name="Service"
    ).namespaces.instantiate(name="Provisioning").namespaces.instantiate(
        name="StateMachines").classes.instantiate(
        name="ServiceProvisionRequestApproval").methods.instantiate(
        name="validate_request")
    return method


@pytest.mark.tier(3)
@pytest.mark.provider([VMwareProvider], scope="module")
@pytest.mark.ignore_stream("5.10")
def test_user_requester_for_lifecycle_provision(request, appliance, provider, setup_provider,
                                                new_users, generic_catalog_item,
                                                infra_validate_request, service_validate_request,
                                                provisioning):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: high
        initialEstimate: 1/6h
        tags: automate

    Bugzilla:
         1671563
         1720273
    """
    script = """
    user = $evm.root['user']
    $evm.log(:info, "This is the user: #{user.userid}")

    $evm.log("info", "Listing Root Object Attributes:")
    $evm.root.attributes.sort.each { |k, v| $evm.log("info", "\t#{k}: #{v}") }
    $evm.log("info", "===========================================")
    """
    infra_validate_request.update(updates={"script": script})
    service_validate_request.update(updates={"script": script})

    with new_users[0]:
        # Log in with first user and order service catalog
        result = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[".*This is the user: {name}.*".format(
                name=new_users[0].credential.principal)],
        )
        result.fix_before_start()
        service_catalogs = ServiceCatalogs(
            appliance, catalog=generic_catalog_item.catalog, name=generic_catalog_item.name
        )
        provision_request = service_catalogs.order()
        provision_request.wait_for_request()
        result.validate_logs()

    with new_users[1]:
        # Log in with second user and provision instance via lifecycle
        result = LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=[".*This is the user: {name}.*".format(
                name=new_users[1].credential.principal)],
        )
        result.fix_before_start()
        prov_data = {
            "catalog": {'vm_name': random_vm_name(context='provision')},
            "environment": {'automatic_placement': True},
        }
        do_vm_provisioning(appliance,
                           template_name=provisioning["template"],
                           provider=provider,
                           vm_name=prov_data['catalog']['vm_name'], provisioning_data=prov_data,
                           wait=False, request=None)
        request_description = 'Provision from [{template}] to [{vm}{msg}]'.format(
            template=provisioning["template"], vm=prov_data['catalog']['vm_name'], msg='')
        provision_request = appliance.collections.requests.instantiate(request_description)
        provision_request.wait_for_request(method='ui')
        request.addfinalizer(provision_request.remove_request)
        result.validate_logs()
