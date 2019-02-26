# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.klass import ClassDetailsView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_method_crud(klass):
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
    view = method.create_view(ClassDetailsView)
    view.flash.assert_message('Automate Method "{}" was added'.format(method.name))
    assert method.exists
    origname = method.name
    with update(method):
        method.name = fauxfactory.gen_alphanumeric(8)
        method.script = "bar"
    assert method.exists
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
    with update(method):
        method.inputs = {}
    view = navigate_to(method, 'Details')
    assert not view.inputs.is_displayed
    method.delete()


@pytest.mark.tier(2)
def test_duplicate_method_disallowed(klass):
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
