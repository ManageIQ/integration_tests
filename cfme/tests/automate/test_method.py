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
def test_method_crud(klass):
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
    with update(method):
        method.name = origname
    assert method.exists
    method.delete()
    assert not method.exists


@pytest.mark.sauce
@pytest.mark.tier(2)
def test_automate_method_inputs_crud(klass):
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
def test_duplicate_method_disallowed(request, klass):
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
