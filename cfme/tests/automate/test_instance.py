# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.mark.sauce
@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-3922')
def test_instance_crud(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/16h
        tags: automate
    """
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
    orig = instance.description
    with update(instance):
        instance.description = 'edited'
    with update(instance):
        instance.description = orig
    instance.delete()
    assert not instance.exists


@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-20871')
def test_duplicate_instance_disallowed(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: high
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
    """
    name = fauxfactory.gen_alphanumeric()
    klass.instances.create(name=name)
    with pytest.raises(Exception, match="Name has already been taken"):
        klass.instances.create(name=name)


@pytest.mark.tier(3)
@pytest.mark.polarion('RHCF3-20872')
def test_instance_display_name_unset_from_ui(klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: high
        initialEstimate: 1/30h
        tags: automate
    """
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric())
    with update(instance):
        instance.display_name = fauxfactory.gen_alphanumeric()
    assert instance.exists
    with update(instance):
        instance.display_name = ""
    assert instance.exists


@pytest.mark.tier(1)
def test_automate_instance_missing(domain, klass, namespace, appliance):
    """If an instance called in class does not exist, a .missing instance is processed if it exists.
    A _missing_instance attribute (which contains the name of the instance that was supposed to be
    called) is then set on $evm.object so it then can be used eg. to resolve methods dynamically.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: high
        initialEstimate: 1/10h
        tags: automate
    """
    catch_string = fauxfactory.gen_alphanumeric()
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, "{}")'.format(catch_string),
    )
    klass.schema.add_fields({'name': 'mfield', 'type': 'Method', 'data_type': 'String'})
    klass.instances.create(name='.missing', fields={'mfield': {'value': '${#_missing_instance}'}})
    klass2 = namespace.classes.create(name=fauxfactory.gen_alpha())
    klass2.schema.add_fields({'name': 'rel', 'type': 'Relationship'})
    instance2 = klass2.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        fields={'rel': {'value': '/' + '/'.join(method.tree_path_name_only[1:])}}
    )
    simulate(
        appliance=appliance,
        request='Call_Instance',
        attributes_values={
            'namespace': '{}/{}'.format(domain.name, namespace.name),
            'class': klass2.name,
            'instance': instance2.name
        }
    )
    assert appliance.ssh_client.run_command(
        'grep {} /var/www/miq/vmdb/log/automation.log'.format(catch_string)).success


@pytest.mark.tier(1)
def test_automate_relationship_trailing_spaces(request, klass, namespace, domain):
    """
    Handle trailing whitespaces in automate instance relationships.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/10h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: Automate
        tags: automate
        title: Test automate relationship trailing spaces
        testSteps:
            1. Create a class and its instance, also create second one,
               that has a relationship field.
            2. Create an instance with the relationship field pointing to the first class'
               instance but add a couple of whitespaces after it.
            3. Execute the AE model, eg. using Simulate.
        expectedResults:
            1.
            2.
            3. Logs contain no resolution errors.

    PR:
        https://github.com/ManageIQ/manageiq/pull/7550
    """
    # Message to display in automation log by executing method of klass
    catch_string = fauxfactory.gen_alphanumeric()

    # Added method1 for klass1
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, "{}")'.format(catch_string)
    )
    request.addfinalizer(method.delete_if_exists)

    # Added schema for klass1 with type method for calling the method1 in same klass1
    klass.schema.add_fields({'name': 'meth', 'type': 'Method', 'data_type': 'String'})

    # Created instance1 to execute method1
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={'meth': {'value': method.name}}
    )
    request.addfinalizer(instance.delete_if_exists)

    # Created klass2 under same domain/namespace
    klass2 = namespace.classes.create(
        name=fauxfactory.gen_alpha(),
        display_name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    request.addfinalizer(klass2.delete_if_exists)

    # Added schema for klass2 with type Relationship for calling instance1 of klass1
    klass2.schema.add_fields({'name': 'rel', 'type': 'Relationship', 'data_type': 'String'})

    # Created instance2 of klass2 and called instance1 of klass1. Here couple of white spaces are
    # added in the value field of rel type.
    instance2 = klass2.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={
            "rel": {
                "value": "/{domain}/{namespace}/{klass}/{instance}   ".format(
                    domain=domain.name,
                    namespace=namespace.name,
                    klass=klass.name,
                    instance=instance.name,
                )
            }
        },
    )
    request.addfinalizer(instance2.delete_if_exists)

    # Checking if automation log is giving resolution error or not by searching 'ERROR'.
    # Also checking if method1 of klass1 is executed successfully or not by searching 'catch_string'
    # in automation log.
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*{}.*".format(catch_string)],
        failure_patterns=[".*ERROR.*"]
    )
    result.start_monitoring()

    # Executing the automate method of klass1 using simulation
    simulate(
        appliance=klass.appliance,
        request="Call_Instance",
        attributes_values={
            "namespace": "{}/{}".format(domain.name, namespace.name),
            "class": klass2.name,
            "instance": instance2.name,
        },
    )
    assert result.validate(wait="60s")


@pytest.fixture(scope="module")
def copy_instance(domain):
    """
    This fixture copies the instance '/ManageIQ/System/Request/ansible_tower_job' to new domain.
    """
    # Instantiating class 'Request'
    klass = (
        domain.parent.instantiate(name="ManageIQ")
        .namespaces.instantiate(name="System")
        .classes.instantiate(name="Request")
    )

    # Instantiating instance 'ansible_tower_job' and copying it to new domain
    klass.instances.instantiate(name="ansible_tower_job").copy_to(domain.name)
    instance = (
        domain.namespaces.instantiate(name="System")
        .classes.instantiate(name="Request")
        .instances.instantiate(name="ansible_tower_job")
    )
    yield instance


@pytest.mark.tier(1)
def test_check_system_request_calls_depr_conf_mgmt(appliance, copy_instance):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Automate
        tags: automate
        setup:
            1. Copy /System/Request/ansible_tower_job instance to new domain
        testSteps:
            1. Run that instance(ansible_tower_job) using simulation
            2. See automation log
        expectedResults:
            1.
            2. The /System/Request/ansible_tower_job instance should call the newer
               "/AutomationManagement/AnsibleTower/Operations/StateMachines/Job/default" method

    Bugzilla:
        1615444
    """
    search = '/AutomationManagement/AnsibleTower/Operations/StateMachines/Job/default'
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*{}.*".format(search)]
    )
    result.start_monitoring()
    # Executing the automate instance - 'ansible_tower_job' using simulation
    simulate(
        appliance=appliance,
        request=copy_instance.name
    )
    assert result.validate(wait="60s")


@pytest.fixture(scope="module")
def copy_quota_instance(domain):
    """Copy the default instance 'quota' to custom domain"""
    miq = domain.appliance.collections.domains.instantiate("ManageIQ")

    original_instance = (
        miq.namespaces.instantiate("System")
        .namespaces.instantiate("CommonMethods")
        .classes.instantiate("QuotaStateMachine")
        .instances.instantiate("quota")
    )
    original_instance.copy_to(domain=domain)

    instance = (
        domain.namespaces.instantiate("System")
        .namespaces.instantiate("CommonMethods")
        .classes.instantiate("QuotaStateMachine")
        .instances.instantiate("quota")
    )
    return instance


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    ("entity", "search"),
    [
        (
            'group',
            'Getting Quota Values for Model',
        ),
        (
            'tenant',
            'Getting Tenant Quota Values for',
        ),
    ],
    ids=["group", "tenant"],
)
def test_quota_source_value(request, entity, search, copy_quota_instance, generic_catalog_item):
    """
    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        startsin: 5.10
        casecomponent: Automate

    Bugzilla:
        1319910
    """
    # Changing quota source value
    copy_quota_instance.update({"fields": {'quota_source_type': {'value': entity}}})

    # Setting cpu quota for 'My Company' tenant
    root_tenant = copy_quota_instance.appliance.collections.tenants.get_root_tenant()
    root_tenant.set_quota(**{"cpu_cb": True, "cpu": 3})
    request.addfinalizer(lambda: root_tenant.set_quota(**{"cpu_cb": False}))

    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", matched_patterns=[".*{}.*".format(search)]
    )
    result.start_monitoring()
    service_catalogs = ServiceCatalogs(
        copy_quota_instance.appliance, catalog=generic_catalog_item.catalog,
        name=generic_catalog_item.name
    )
    request_description = 'Provisioning Service [{name}] from [{name}]'.format(
        name=service_catalogs.name)
    provision_request = copy_quota_instance.appliance.collections.requests.instantiate(
        description=request_description)
    service_catalogs.order()
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(lambda: provision_request.remove_request(method="rest"))
    assert result.validate(wait="60s")
