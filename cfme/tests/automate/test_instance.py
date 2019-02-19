# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
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
