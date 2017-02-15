# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.explorer.domain import DomainCollection

from utils import error
from utils.update import update


@pytest.mark.tier(1)
@pytest.mark.parametrize('enabled', [True, False], ids=['enabled', 'disabled'])
def test_domain_crud(request, enabled):
    domains = DomainCollection()
    domain = domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=enabled)
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
    # TODO: Verify details
    updated_description = "editdescription{}".format(fauxfactory.gen_alpha())
    with update(domain):
        domain.description = updated_description
    assert domain.exists
    domain.delete(cancel=True)
    assert domain.exists
    domain.delete()
    assert not domain.exists


@pytest.mark.tier(1)
def test_domain_delete_from_table(request):
    domains = DomainCollection()
    generated = []
    for _ in range(3):
        domain = domains.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            enabled=True)
        request.addfinalizer(domain.delete_if_exists)
        generated.append(domain)

    domains.delete(*generated)
    for domain in generated:
        assert not domain.exists


@pytest.mark.tier(2)
def test_duplicate_domain_disallowed(request):
    domains = DomainCollection()
    domain = domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    with error.expected("Name has already been taken"):
        domains.create(
            name=domain.name,
            description=domain.description,
            enabled=domain.enabled)
