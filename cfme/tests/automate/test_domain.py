# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.import_export import AutomateGitRepository
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update

pytestmark = [test_requirements.automate]


@pytest.mark.sauce
@pytest.mark.tier(1)
@pytest.mark.parametrize('enabled', [True, False], ids=['enabled', 'disabled'])
def test_domain_crud(request, enabled, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        initialEstimate: 1/30h
        tags: automate
    """
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=enabled)
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
    view = navigate_to(domain, 'Details')
    if enabled:
        assert 'Disabled' not in view.title.text
    else:
        assert 'Disabled' in view.title.text
    updated_description = "editdescription{}".format(fauxfactory.gen_alpha())
    with update(domain):
        domain.description = updated_description
    view = navigate_to(domain, 'Edit')
    assert view.description.value == updated_description
    assert domain.exists
    domain.delete(cancel=True)
    assert domain.exists
    domain.delete()
    assert not domain.exists


@pytest.mark.tier(1)
def test_domain_edit_enabled(domain, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/16h
        caseimportance: high
        tags: automate
    """
    assert domain.exists
    view = navigate_to(domain, 'Details')
    assert 'Disabled' not in view.title.text
    with update(domain):
        domain.enabled = False
    view = navigate_to(domain, 'Details')
    assert 'Disabled' in view.title.text


@pytest.mark.tier(2)
def test_domain_lock_disabled(request, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/16h
        tags: automate
    """
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=False)
    request.addfinalizer(domain.delete_if_exists)
    domain.lock()
    view = navigate_to(domain, 'Details')
    assert 'Disabled' in view.title.text
    assert 'Locked' in view.title.text


@pytest.mark.tier(1)
def test_domain_delete_from_table(request, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/30h
        tags: automate
    """
    generated = []
    for _ in range(3):
        domain = appliance.collections.domains.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            enabled=True)
        request.addfinalizer(domain.delete_if_exists)
        generated.append(domain)

    appliance.collections.domains.delete(*generated)
    for domain in generated:
        assert not domain.exists


@pytest.mark.tier(2)
def test_duplicate_domain_disallowed(domain, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
    """
    assert domain.exists
    with pytest.raises(Exception, match="Name has already been taken"):
        appliance.collections.domains.create(
            name=domain.name,
            description=domain.description,
            enabled=domain.enabled)


@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-11228')
def test_domain_cannot_delete_builtin(appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/16h
        tags: automate
    """
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
@pytest.mark.polarion('RHCF3-11227')
def test_domain_cannot_edit_builtin(appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: critical
        caseposneg: negative
        initialEstimate: 1/16h
        tags: automate
    """
    manageiq_domain = appliance.collections.domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
def test_domain_name_wrong(appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/60h
        tags: automate
    """
    with pytest.raises(Exception, match='Name may contain only'):
        appliance.collections.domains.create(name='with space')


@pytest.mark.tier(2)
def test_domain_lock_unlock(domain, appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/16h
        caseimportance: medium
        tags: automate
    """
    assert domain.exists
    ns1 = domain.namespaces.create(name='ns1')
    ns2 = ns1.namespaces.create(name='ns2')
    cls = ns2.classes.create(name='class1')
    cls.schema.add_field(name='myfield', type='Relationship')
    inst = cls.instances.create(name='inst')
    meth = cls.methods.create(name='meth', script='$evm')
    # Lock the domain
    domain.lock()
    details = navigate_to(ns1, 'Details')
    assert not details.configuration.is_displayed
    details = navigate_to(ns2, 'Details')
    assert not details.configuration.is_displayed
    # class
    details = navigate_to(cls, 'Details')
    if appliance.version < '5.10':
        assert details.configuration.items == ['Copy selected Instances']
        assert not details.configuration.item_enabled('Copy selected Instances')
    else:
        assert not details.configuration.is_enabled
    details.schema.select()
    assert not details.configuration.is_displayed
    # instance
    details = navigate_to(inst, 'Details')
    if appliance.version < '5.10':
        assert details.configuration.items == ['Copy this Instance']
    else:
        assert not details.configuration.is_enabled
    # method
    details = navigate_to(meth, 'Details')
    if appliance.version < '5.10':
        assert details.configuration.items == ['Copy this Method']
    else:
        assert not details.configuration.is_enabled
    # Unlock it
    domain.unlock()
    # Check that it is editable
    with update(ns1):
        ns1.name = 'UpdatedNs1'
    assert ns1.exists
    with update(ns2):
        ns2.name = 'UpdatedNs2'
    assert ns2.exists
    with update(cls):
        cls.name = 'UpdatedClass'
    assert cls.exists
    cls.schema.add_field(name='myfield2', type='Relationship')
    with update(inst):
        inst.name = 'UpdatedInstance'
    assert inst.exists
    with update(meth):
        meth.name = 'UpdatedMethod'
    assert meth.exists


@pytest.mark.parametrize(
    ('url', 'param_type', 'param_value', 'verify_ssl'),
    [
        ('https://github.com/ramrexx/CloudForms_Essentials.git', 'branch', 'origin/cf4.1', True),
        ('https://github.com/RedHatQE/ManageIQ-automate-git.git', 'tag', '0.1', False)
    ])
@pytest.mark.meta(server_roles=['+git_owner'])
@pytest.mark.tier(1)
def test_domain_import_git(request, appliance, url, param_type, param_value, verify_ssl):
    """Verifies that a domain can be imported from git.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        initialEstimate: 1/20h
        caseimportance: medium
        tags: automate
    """
    repo = AutomateGitRepository(url=url, verify_ssl=verify_ssl, appliance=appliance)
    domain = repo.import_domain_from(**{param_type: param_value})
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
    domain.delete()
