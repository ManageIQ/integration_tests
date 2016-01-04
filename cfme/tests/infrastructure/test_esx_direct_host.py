# -*- coding: utf-8 -*-
""" Tests of managing ESX hypervisors directly. If another direct ones will be supported, it should
not be difficult to extend the parametrizer.

"""
import pytest

from cfme.infrastructure.provider import VMwareProvider
from utils.conf import cfme_data, credentials
from utils.net import resolve_hostname
from utils.providers import get_crud
from utils.version import Version


def pytest_generate_tests(metafunc):
    arg_names = "_provider", "original_provider_key"
    arg_values = []
    arg_ids = []
    for provider_key, provider in cfme_data.get("management_systems", {}).iteritems():
        if provider["type"] != "virtualcenter":
            continue
        hosts = provider.get("hosts", [])
        if not hosts:
            continue

        version = provider.get("version", None)
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
        provider_data.update(provider)
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
        arg_values.append([host_provider, provider_key])
        arg_ids.append("{}/{}".format(provider_key, host["name"]))
    metafunc.parametrize(arg_names, arg_values, ids=arg_ids, scope="module")


@pytest.yield_fixture(scope="module")
def provider(_provider, original_provider_key):
    original_provider = get_crud(original_provider_key)
    if original_provider.exists:
        # Delete original provider's hosts first
        for host in original_provider.hosts:
            if host.exists:
                host.delete(cancel=False)
        # Get rid of the original provider, it would make a mess.
        original_provider.delete(cancel=False)
        original_provider.wait_for_delete()
    yield _provider
    for host in _provider.hosts:
        if host.exists:
            host.delete(cancel=False)
    _provider.delete(cancel=False)
    _provider.wait_for_delete()


def test_validate(provider):
    """Tests that the CFME can manage also just the hosts of VMware.

    Prerequisities:
        * A CFME and a VMware provider (not setup in the CFME yet).

    Steps:
        * Use the IP address of a host of the VMware provider and its credentials and use them to
            set up a VMware provider.
        * Refresh the provider
        * The provider should refresh without problems.
    """
    provider.create()
    provider.refresh_provider_relationships()
    provider.validate()
