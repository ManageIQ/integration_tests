# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
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
@pytest.mark.polarion('RHCF3-3922')
def test_instance_crud(klass):
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
def test_duplicate_instance_disallowed(request, klass):
    name = fauxfactory.gen_alphanumeric()
    klass.instances.create(name=name)
    with pytest.raises(Exception, match="Name has already been taken"):
        klass.instances.create(name=name)


@pytest.mark.meta(blockers=[1148541])
@pytest.mark.tier(3)
@pytest.mark.polarion('RHCF3-20872')
def test_instance_display_name_unset_from_ui(request, klass):
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric())
    with update(instance):
        instance.display_name = fauxfactory.gen_alphanumeric()
    assert instance.exists
    with update(instance):
        instance.display_name = ""
    assert instance.exists
