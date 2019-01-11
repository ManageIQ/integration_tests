# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.fixture(scope='module')
def domain(appliance):
    dc = DomainCollection(appliance)
    d = dc.create(
        name='test_{}'.format(fauxfactory.gen_alpha()),
        description='desc_{}'.format(fauxfactory.gen_alpha()),
        enabled=True)
    yield d
    d.delete()


@pytest.fixture(scope="module")
def namespace(request, domain):
    return domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )


@pytest.fixture(scope="module")
def klass(request, namespace):
    return namespace.classes.create(
        name=fauxfactory.gen_alpha(),
        display_name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_method_crud(appliance, klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/16h
        tags: automate
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    assert method.exists
    origname = method.name
    with update(method):
        method.name = fauxfactory.gen_alphanumeric(8)
        method.script = "bar"
    assert method.exists
    navigate_to(appliance.server, 'Dashboard')
    # Navigation to 'Dashboard' is required to navigate to details page of method.
    # So that 'Edit this Method' option from configuration will be selected from details page.
    with update(method):
        method.name = origname
    assert method.exists
    method.delete()
    assert not method.exists


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_automate_method_inputs_crud(appliance, klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/8h
        caseimportance: critical
        tags: automate
    """
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='blah',
        inputs={
            'foo': {'data_type': 'string'},
            'bar': {'data_type': 'integer', 'default_value': '42'}}
    )
    assert method.exists
    view = navigate_to(method, 'Details')
    assert view.inputs.is_displayed
    assert view.inputs.read() == {
        'foo': {'Data Type': 'string', 'Default Value': ''},
        'bar': {'Data Type': 'integer', 'Default Value': '42'},
    }
    with update(method):
        method.inputs = {'different': {'default_value': 'value'}}
    view = navigate_to(method, 'Details')
    assert view.inputs.is_displayed
    assert view.inputs.read() == {
        'different': {'Data Type': 'string', 'Default Value': 'value'},
    }
    navigate_to(appliance.server, 'Dashboard')
    # Navigation to 'Dashboard' is required to navigate on details page of method.
    # So that 'Edit this Method' option from configuration will be selected from details page.
    with update(method):
        method.inputs = {}
    view = navigate_to(method, 'Details')
    assert not view.inputs.is_displayed
    method.delete()


@pytest.mark.tier(2)
def test_duplicate_method_disallowed(request, klass):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseposneg: negative
        initialEstimate: 1/10h
        caseimportance: critical
        tags: automate
    """
    name = fauxfactory.gen_alpha()
    klass.methods.create(
        name=name,
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    with pytest.raises(Exception, match="Name has already been taken"):
        klass.methods.create(
            name=name,
            location='inline',
            script='$evm.log(:info, ":P")',
        )
