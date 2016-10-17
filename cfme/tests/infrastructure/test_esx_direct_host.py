# -*- coding: utf-8 -*-
""" Tests of managing ESX hypervisors directly. If another direct ones will be supported, it should
not be difficult to extend the parametrizer.

"""
import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from utils.conf import credentials
from utils.net import resolve_hostname
from utils import testgen
from utils.version import Version


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.provider_by_type(metafunc, ['virtualcenter'])
    argnames = argnames + ["_host_provider"]

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        # TODO
        # All this should be replaced with a proper ProviderFilter passed to testgen.providers()
        if args['provider'].type != "virtualcenter":
            continue
        hosts = args['provider'].data.get("hosts", [])
        if not hosts:
            continue

        version = args['provider'].data.get("version", None)
        if version is None:
            # No version, no test
            continue
        if Version(version) < "5.0":
            # Ignore lesser than 5
            continue

        host = hosts[0]
        creds = credentials[host["credentials"]]
        ip_address = resolve_hostname(host["name"])
        cred = VMwareProvider.Credential(
            principal=creds["username"],
            secret=creds["password"],
            verify_secret=creds["password"]
        )
        # Mock provider data
        provider_data = {}
        provider_data.update(args['provider'].data)
        provider_data["name"] = host["name"]
        provider_data["hostname"] = host["name"]
        provider_data["ipaddress"] = ip_address
        provider_data["credentials"] = host["credentials"]
        provider_data.pop("host_provisioning", None)
        provider_data["hosts"] = [host]
        provider_data["discovery_range"] = {}
        provider_data["discovery_range"]["start"] = ip_address
        provider_data["discovery_range"]["end"] = ip_address
        host_provider = VMwareProvider(
            name=host["name"],
            hostname=host["name"],
            ip_address=ip_address,
            credentials={'default': cred},
            provider_data=provider_data,
        )
        argvalues[i].append(host_provider)
        idlist[i] = "{}/{}".format(args['provider'].key, host["name"])
        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.yield_fixture(scope="module")
def host_provider(_host_provider, provider):
    if provider.exists:
        # Delete original provider's hosts first
        for host in provider.hosts:
            if host.exists:
                host.delete(cancel=False)
        # Get rid of the original provider, it would make a mess.
        provider.delete(cancel=False)
        provider.wait_for_delete()
    yield _host_provider
    for host in _host_provider.hosts:
        if host.exists:
            host.delete(cancel=False)
    _host_provider.delete(cancel=False)
    _host_provider.wait_for_delete()


@pytest.mark.tier(2)
def test_validate(host_provider):
    """Tests that the CFME can manage also just the hosts of VMware.

    Prerequisities:
        * A CFME and a VMware provider (not setup in the CFME yet).

    Steps:
        * Use the IP address of a host of the VMware provider and its credentials and use them to
            set up a VMware provider.
        * Refresh the provider
        * The provider should refresh without problems.
    """
    host_provider.create()
    host_provider.refresh_provider_relationships()
    host_provider.validate()
